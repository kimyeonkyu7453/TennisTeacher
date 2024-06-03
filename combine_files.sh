#!/bin/sh

# Define the output file
output_path="/app/openpose/pose_lib/pose_iter_160000.caffemodel"

# Check if the output file already exists and remove it
if [ -f "$output_path" ]; then
  rm "$output_path"
fi

# Concatenate all the split files
cat /app/openpose/pose_lib/pose_iter_160000.caffemodel.part-* > "$output_path"

# Set the correct permissions
chmod 777 "$output_path"
