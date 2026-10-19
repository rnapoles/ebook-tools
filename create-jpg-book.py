#!/usr/bin/env python3
"""
create-jpg-book.py

Toma todas las imágenes JPG de una carpeta y genera un ebook en formato EPUB,
con una imagen por página, en orden alfabético/numérico según el nombre de archivo.

Requisitos:
    pip install ebooklib Pillow

Uso:
    python create-jpg-book.py /ruta/a/carpeta_imagenes -o mi_libro.epub -t "Mi Ebook" -a "Autor"
"""

import argparse
import os
import re
import sys
import uuid

from PIL import Image
from ebooklib import epub


def orden_natural(nombre):
    """Permite que 'img2.jpg' vaya antes que 'img10.jpg'."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', nombre)]


def obtener_imagenes(carpeta):
    extensiones = ('.jpg', '.jpeg')
    archivos = [
        f for f in os.listdir(carpeta)
        if f.lower().endswith(extensiones)
    ]
    archivos.sort(key=orden_natural)
    return archivos


def crear_epub(carpeta, salida, titulo, autor, idioma):
    imagenes = obtener_imagenes(carpeta)
    if not imagenes:
        print(f"No se encontraron imágenes JPG en: {carpeta}")
        sys.exit(1)

    print(f"Se encontraron {len(imagenes)} imágenes. Generando ebook...")

    libro = epub.EpubBook()
    libro.set_identifier(str(uuid.uuid4()))
    libro.set_title(titulo)
    libro.set_language(idioma)
    libro.add_author(autor)

    capitulos = []

    for i, nombre_archivo in enumerate(imagenes, start=1):
        ruta_completa = os.path.join(carpeta, nombre_archivo)

        # Leer bytes de la imagen y asegurarnos de que sea JPEG válido
        with Image.open(ruta_completa) as img:
            img = img.convert("RGB")
            img_bytes_path = f"images/img_{i:04d}.jpg"

        with open(ruta_completa, 'rb') as f:
            contenido_imagen = f.read()

        # Añadir imagen como recurso del EPUB
        item_imagen = epub.EpubItem(
            uid=f"img_{i}",
            file_name=img_bytes_path,
            media_type="image/jpeg",
            content=contenido_imagen
        )
        libro.add_item(item_imagen)

        # Crear página HTML que muestra la imagen a pantalla completa
        pagina_html = epub.EpubHtml(
            title=f"Página {i}",
            file_name=f"page_{i:04d}.xhtml",
            lang=idioma
        )
        pagina_html.content = f'''
        <html>
        <head><style>
            body {{ margin:0; padding:0; text-align:center; }}
            img {{ max-width:100%; max-height:100vh; display:block; margin:0 auto; }}
        </style></head>
        <body>
            <img src="{img_bytes_path}" alt="{nombre_archivo}"/>
        </body>
        </html>
        '''
        libro.add_item(pagina_html)
        capitulos.append(pagina_html)

    # Tabla de contenidos y estructura de navegación
    libro.toc = tuple(capitulos)
    libro.add_item(epub.EpubNcx())
    libro.add_item(epub.EpubNav())
    libro.spine = ['nav'] + capitulos

    epub.write_epub(salida, libro)
    print(f"✅ Ebook creado exitosamente: {salida}")


def main():
    parser = argparse.ArgumentParser(
        description="Crea un ebook EPUB a partir de imágenes JPG de una carpeta."
    )
    parser.add_argument("carpeta", help="Ruta a la carpeta con las imágenes JPG")
    parser.add_argument("-o", "--salida", default="ebook.epub", help="Nombre del archivo EPUB de salida")
    parser.add_argument("-t", "--titulo", default="Mi Ebook", help="Título del ebook")
    parser.add_argument("-a", "--autor", default="Autor Desconocido", help="Autor del ebook")
    parser.add_argument("-l", "--idioma", default="es", help="Código de idioma (ej: es, en)")

    args = parser.parse_args()

    if not os.path.isdir(args.carpeta):
        print(f"Error: la carpeta '{args.carpeta}' no existe.")
        sys.exit(1)

    crear_epub(args.carpeta, args.salida, args.titulo, args.autor, args.idioma)


if __name__ == "__main__":
    main()