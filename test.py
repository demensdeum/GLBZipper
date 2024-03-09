#!/usr/bin/env python

import os
import json
import tempfile
from gltflib import GLTF
import subprocess
import copy
import shutil
import json

def format_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_in_bytes)
    for unit in units[:-1]:
        if size < 1024.0:
            break
        size /= 1024.0

    return f"{size:.2f} {unit}"

def png_to_jpg(source_file, output_file):
    print(source_file)
    print(output_file)
    subprocess.run(['magick', 'convert', source_file, '-quality', '75', '-resize', '256x256', output_file])

def glb_to_gltf(source_path, output_path, resources_filepath):
    gltf = GLTF.load(source_path)
    glb_resource = gltf.get_glb_resource()
    gltf.convert_to_file_resource(glb_resource, resources_filepath)
    gltf.export(output_path)

def replace_truncate_align(original_file_path, insert_data_file_path, offset, length, output_file_path):
    with open(original_file_path, 'rb') as original_file:
        original_data = bytearray(original_file.read())

    with open(insert_data_file_path, 'rb') as replacement_file:
        replacement_data = bytearray(replacement_file.read())

    replacement_data_length = len(replacement_data)

    padding_byte = 0x20
    need_padding_bytes_length = 4 - replacement_data_length % 4
    print(f"need_padding_bytes_length: {need_padding_bytes_length}")
    for i in range(need_padding_bytes_length):
        replacement_data.append(0x20)
        replacement_data_length = len(replacement_data)
        print(replacement_data_length % 4)        

    replacement_data_length = len(replacement_data)
    print(replacement_data_length % 4)

    original_data[offset:offset + length] = replacement_data

    print(f"{format_size(replacement_data_length)} / {format_size(length)}")

    if replacement_data_length < length:
        original_size = len(original_data)
        del original_data[offset + replacement_data_length : offset + length]
        changed_size = len(original_data)
        print(f"{format_size(original_size)} / {format_size(changed_size)}")

    with open(output_file_path, 'wb') as output_file:
        output_file.write(original_data)

    return replacement_data_length

def compress_textures(gltf_path, temporary_gltf_file, resources_filepath, output_file_path):
    temporary_directory = tempfile.gettempdir()
    print(gltf_path)
    f = open(gltf_path)
    gltf_file = json.load(f)
    output_gltf_file = copy.deepcopy(gltf_file)
    resource = open(resources_filepath, "rb")
    output_resources_filepath = f"{resources_filepath}.output"
    shutil.copy(resources_filepath, output_resources_filepath)
    for index, image in enumerate(gltf_file["images"]):
        buffer_view = gltf_file["bufferViews"][image["bufferView"]]
        start_byte = buffer_view["byteOffset"]
        byte_length = buffer_view["byteLength"]
        if image["mimeType"] == "image/png":
            image_file_name = f"gltf-temp-{image['name']}.png"
            image_file_path = os.path.join(temporary_directory, image_file_name)
            output_image_file = open(image_file_path, "wb")
            resource.seek(start_byte)    
            output_image_file.write(resource.read(byte_length))
            compressed_image_name = f"{image_file_path[:-4]}.jpg"
            png_to_jpg(image_file_path, compressed_image_name)
            byte_length_compressed = replace_truncate_align(output_resources_filepath, compressed_image_name, start_byte, byte_length, output_resources_filepath)

            output_gltf_file["images"][index]["mimeType"] = "image/jpeg"
            output_gltf_file["bufferViews"][output_gltf_file["images"][index]["bufferView"]]["byteOffset"] = start_byte
            output_gltf_file["bufferViews"][output_gltf_file["images"][index]["bufferView"]]["byteLength"] = byte_length_compressed
            ground_byte = start_byte + byte_length_compressed
            for output_buffer_view in output_gltf_file["bufferViews"]:
                if output_buffer_view["byteOffset"] >= ground_byte:
                    output_buffer_view["byteOffset"] -= ground_byte

    output_gltf_file["buffers"][0]["uri"] = output_resources_filepath
    output_gltf_file_path = f"{gltf_path}.altered.gltf"

    with open(output_gltf_file_path, 'w') as json_file:
        json.dump(output_gltf_file, json_file)
    
    output_glb = GLTF.load(output_gltf_file_path)
    output_glb.export(output_file_path)

def compress_glb(source_path, output_path):
    temporary_directory = tempfile.gettempdir()
    print(f"temporary_directory: {temporary_directory}")
    temporary_gltf_file = os.path.join(temporary_directory, "gltf-temp.gltf")
    temporaty_resources_filepath = f"{temporary_gltf_file}.bin"
    print(f"f{temporaty_resources_filepath}")
    glb_to_gltf(source_path, temporary_gltf_file, temporaty_resources_filepath)
    compress_textures(temporary_gltf_file, temporary_gltf_file, temporaty_resources_filepath, output_path)

compress_glb("cat.glb", "compressed.glb")
