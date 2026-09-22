import os
import sys
import time
import zlib
import lzma
import hashlib
import shutil
import struct
import tkinter as tk
from tkinter import filedialog

os.system('')

print(r"""
            ________      ________      ________      ________ 
---------- |\_____  \    |\   __  \    |\   __  \    |\  _____\----------------
----------  \|___/  /|   \ \  \|\  \   \ \  \|\  \   \ \  \__/ ---------------
--------------  /  / /    \ \   __  \   \ \   _  _\   \ \   __\--------------
-------------- /  /_/__    \ \  \ \  \   \ \  \\  \|   \ \  \_|----------------
------------- |\________\   \ \__\ \__\   \ \__\\ _\    \ \__\ ----------------
-------------- \|_______|    \|__|\|__|    \|__|\|__|    \|__| -----------------
""")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_red(msg):
    print(f"{Colors.RED}{msg}{Colors.RESET}")

def print_green(msg):
    print(f"{Colors.GREEN}{msg}{Colors.RESET}")

def print_cyan(msg):
    print(f"{Colors.CYAN}{msg}{Colors.RESET}")

print_green("Parche textos en español DJFFNY Xbox-Compatible con Xbox 360")

def compute_crc32(filepath):
    crc = 0
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF

def apply_zarf_patch():
    patch_path = "parche.ZARF"

    if not os.path.exists(patch_path):
        print_red("Error parche ZARF no encontrado")
        input("Presione ENTER para salir...")
        return

    with open(patch_path, 'rb') as f:
        file_bytes = f.read()

    if len(file_bytes) < 32:
        print_red("parche incompatible o corrupto")
        input("Presione ENTER para salir...")
        return

    patch_data_part = file_bytes[:-16]
    expected_md5 = file_bytes[-16:]
    calculated_md5 = hashlib.md5(patch_data_part).digest()

    if calculated_md5 != expected_md5:
        print_red("parche incompatible o corrupto (MD5 inválido)")
        input("Presione ENTER para salir...")
        return

    if not file_bytes.startswith(b'ZARFC\x01'):
        print_red("parche incompatible o corrupto (Encabezado ZARFC no encontrado)")
        input("Presione ENTER para salir...")
        return

    print_cyan("Descomprimiendo datos del parche en memoria...")
    try:
        compressed_payload = file_bytes[6:-16]
        zarf_bytes = lzma.decompress(compressed_payload)
    except Exception as e:
        print_red(f"Error al descomprimir el parche: {e}")
        input("Presione ENTER para salir...")
        return

    if not zarf_bytes.startswith(b'ZARF\x00\x03'):
        print_red("Estructura interna de parche incompatible")
        input("Presione ENTER para salir...")
        return

    for i in range(5, 0, -1):
        print(f"Abriendo ventana en {i}...", end='\r')
        time.sleep(1)
    print(" " * 30, end='\r')

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    target_dir = filedialog.askdirectory(title="Seleccione la carpeta con los archivos a parchear")
    root.destroy()

    if not target_dir:
        print_red("No se seleccionó ninguna carpeta.")
        input("Presione ENTER para salir...")
        return

    xbe_path = os.path.join(target_dir, "default.xbe")
    if not os.path.exists(xbe_path):
        print_red("Error de comprobación")
        input("Presione ENTER para salir...")
        return

    xbe_crc = compute_crc32(xbe_path)
    if xbe_crc != 0x7A587526:
        print_red("Error de comprobación")
        input("Presione ENTER para salir...")
        return

    num_pointers = struct.unpack('>I', zarf_bytes[6:10])[0]

    pointers = []
    for i in range(num_pointers):
        ptr_offset = 0x10 + (i * 4)
        ptr_val = struct.unpack('>I', zarf_bytes[ptr_offset:ptr_offset+4])[0]
        pointers.append(ptr_val)

    file_map = {}
    for root_path, _, files in os.walk(target_dir):
        for file_name in files:
            full_path = os.path.join(root_path, file_name)
            try:
                c32 = compute_crc32(full_path)
                if c32 not in file_map:
                    file_map[c32] = []
                file_map[c32].append(full_path)
            except Exception:
                pass

    total_files = 0
    for ptr in pointers:
        orig_crc = struct.unpack('>I', zarf_bytes[ptr:ptr+4])[0]
        matching_files = file_map.get(orig_crc, [])
        total_files += max(len(matching_files), 1)

    processed_files_count = 0

    for ptr in pointers:
        curr_offset = ptr

        orig_crc = struct.unpack('>I', zarf_bytes[curr_offset:curr_offset+4])[0]
        curr_offset += 4

        start_patch_offset = struct.unpack('>I', zarf_bytes[curr_offset:curr_offset+4])[0]
        curr_offset += 4

        matching_files = file_map.get(orig_crc, [])
        if not matching_files:
            print_red(f"Error: No se encontró ningún archivo con el CRC32 0x{orig_crc:08X} original.")
            input("Presione ENTER para salir...")
            return

        target_file = matching_files[0]
        rel_path = os.path.relpath(target_file, target_dir)

        processed_files_count += 1
        pct = (processed_files_count / total_files) * 100
        print_cyan(f"[{pct:.1f}%] ({processed_files_count}/{total_files})")
        print(f"Aplicando a {rel_path}")

        with open(target_file, 'rb') as f:
            file_data = bytearray(f.read())

        file_done = False

        while not file_done:
            byte_to_write = zarf_bytes[curr_offset]
            curr_offset += 1

            current_file_ptr = start_patch_offset
            byte_done = False

            while not byte_done and not file_done:
                if curr_offset + 2 > len(zarf_bytes):
                    file_done = True
                    break

                qty = struct.unpack('>H', zarf_bytes[curr_offset:curr_offset+2])[0]
                curr_offset += 2

                if qty == 0:
                    sub_term = zarf_bytes[curr_offset:curr_offset+2]
                    curr_offset += 2

                    if sub_term == b'\x00\x00':
                        byte_done = True
                    elif sub_term == b'\xFF\xFF':
                        file_done = True
                        byte_done = True
                else:
                    jump = struct.unpack('>I', zarf_bytes[curr_offset:curr_offset+4])[0]
                    curr_offset += 4

                    current_file_ptr += jump

                    needed_size = current_file_ptr + qty
                    if len(file_data) < needed_size:
                        file_data.extend(b'\x00' * (needed_size - len(file_data)))

                    for k in range(qty):
                        file_data[current_file_ptr + k] = byte_to_write

                    current_file_ptr += qty

        expected_mod_size = struct.unpack('>I', zarf_bytes[curr_offset:curr_offset+4])[0]
        curr_offset += 4

        expected_mod_crc = struct.unpack('>I', zarf_bytes[curr_offset:curr_offset+4])[0]
        curr_offset += 4

        if len(file_data) > expected_mod_size:
            file_data = file_data[:expected_mod_size]
        elif len(file_data) < expected_mod_size:
            file_data.extend(b'\x00' * (expected_mod_size - len(file_data)))

        with open(target_file, 'wb') as f:
            f.write(file_data)

        actual_crc = compute_crc32(target_file)

        if actual_crc != expected_mod_crc:
            print_red(f"Error de comprobación para {rel_path}")
            print_red(f"Esperado: 0x{expected_mod_crc:08X} - Obtenido: 0x{actual_crc:08X}")
            input("Presione ENTER para salir...")
            return

        if len(matching_files) > 1:
            for dup_file in matching_files[1:]:
                processed_files_count += 1
                dup_rel_path = os.path.relpath(dup_file, target_dir)
                pct = (processed_files_count / total_files) * 100
                print_cyan(f"[{pct:.1f}%] ({processed_files_count}/{total_files})")
                print(f"Aplicando a {dup_rel_path}")
                shutil.copy2(target_file, dup_file)

    print_green("Parche aplicado con éxito :)")
    input("Presione ENTER para salir...")

if __name__ == "__main__":
    apply_zarf_patch()
