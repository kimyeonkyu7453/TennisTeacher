import glob

output_file = '/front/openpose/pose_lib/pose_iter_160000.caffemodel'
input_pattern = '/front/openpose/pose_lib/segment_*'

with open(output_file, 'wb') as f:
    for part in sorted(glob.glob(input_pattern)):
        with open(part, 'rb') as p:
            f.write(p.read())

