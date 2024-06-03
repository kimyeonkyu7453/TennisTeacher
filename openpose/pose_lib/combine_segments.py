import glob
import os

def combine_files():
    segment_dir = '/app/openpose/pose_lib'
    output_file = os.path.join(segment_dir, 'pose_iter_160000.caffemodel')
    input_pattern = os.path.join(segment_dir, 'segment_*')

    with open(output_file, 'wb') as f:
        for part in sorted(glob.glob(input_pattern)):
            with open(part, 'rb') as p:
                f.write(p.read())

    # Set the correct permissions
    os.chmod(output_file, 0o777)

if __name__ == '__main__':
    combine_files()
