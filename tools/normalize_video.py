"""Make a separate seek-friendly MP4 for slow or irregular videos. Never overwrite the source or output."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def normalize(source, output, ffmpeg="ffmpeg"):
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if not source.is_file() or source == output or output.exists() or output.suffix.lower() != ".mp4":
        raise ValueError("Choose an existing video and a new, different .mp4 output path.")
    if not output.parent.is_dir():
        raise ValueError("The output directory must already exist.")
    handle, temporary = tempfile.mkstemp(prefix=".football-normalize-", suffix=".mp4", dir=output.parent)
    os.close(handle)
    process = None
    try:
        # Only the uniquely reserved temporary file is overwritten; -nostdin keeps terminal input with this wrapper.
        process = subprocess.Popen([ffmpeg, "-nostdin", "-hide_banner", "-y", "-fflags", "+genpts", "-i", str(source),
                                    "-map", "0:v:0", "-map", "0:a:0?", "-vf", "fps=30,pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                    "-preset", "fast", "-crf", "20", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
                                    "-c:a", "aac", "-movflags", "+faststart", temporary])
        if process.wait():
            raise RuntimeError("FFmpeg could not normalize this video. The original is unchanged.")
        # Atomic no-clobber publication, including a competing writer creating output during encoding.
        os.link(temporary, output)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        Path(temporary).unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    try:
        target = normalize(args.source, args.output, args.ffmpeg)
    except KeyboardInterrupt:
        parser.exit(130, "Cancelled. Original video preserved.\n")
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"Created {target}. Upload and label this copy separately; its video hash has changed.")


if __name__ == "__main__":
    main()
