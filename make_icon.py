from PIL import Image, ImageDraw

def make_icon(size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    s = size
    pad = int(s * 0.08)

    # Sombra del papel
    shadow_offset = int(s * 0.03)
    d.rounded_rectangle(
        [pad + shadow_offset, pad + shadow_offset, s - pad + shadow_offset, s - pad + shadow_offset],
        radius=int(s * 0.1),
        fill=(180, 200, 220, 120)
    )

    # Papel
    d.rounded_rectangle(
        [pad, pad, s - pad, s - pad],
        radius=int(s * 0.1),
        fill=(244, 248, 252, 255),
        outline=(197, 213, 232, 255),
        width=max(1, int(s * 0.012))
    )

    # Línea superior decorativa (header)
    header_h = int(s * 0.18)
    d.rounded_rectangle(
        [pad, pad, s - pad, pad + header_h],
        radius=int(s * 0.1),
        fill=(91, 155, 213, 255)
    )
    # Esquinas inferiores del header rectas
    d.rectangle(
        [pad, pad + header_h // 2, s - pad, pad + header_h],
        fill=(91, 155, 213, 255)
    )

    # 3 filas de checklist
    rows = 3
    row_start_y = pad + header_h + int(s * 0.08)
    row_gap = int(s * 0.2)
    box_size = int(s * 0.1)
    box_x = pad + int(s * 0.1)
    line_x1 = box_x + box_size + int(s * 0.06)
    line_x2 = s - pad - int(s * 0.1)

    for i in range(rows):
        y = row_start_y + i * row_gap
        cx = box_x
        cy = y

        if i < 2:
            # Checkbox marcado (azul)
            d.rounded_rectangle(
                [cx, cy, cx + box_size, cy + box_size],
                radius=int(box_size * 0.25),
                fill=(91, 155, 213, 255)
            )
            # Checkmark blanco
            ck = int(box_size * 0.15)
            pts = [
                cx + ck, cy + box_size // 2,
                cx + box_size // 2 - ck // 2, cy + box_size - ck * 2,
                cx + box_size - ck, cy + ck * 2
            ]
            d.line(pts, fill=(255, 255, 255, 255), width=max(2, int(box_size * 0.18)))
        else:
            # Checkbox vacío
            d.rounded_rectangle(
                [cx, cy, cx + box_size, cy + box_size],
                radius=int(box_size * 0.25),
                fill=(255, 255, 255, 255),
                outline=(197, 213, 232, 255),
                width=max(1, int(box_size * 0.12))
            )

        # Línea de texto
        line_color = (143, 168, 192, 200) if i < 2 else (44, 62, 80, 220)
        line_y = cy + box_size // 2
        line_w = line_x2 if i == 0 else int(line_x1 + (line_x2 - line_x1) * 0.75)
        d.rounded_rectangle(
            [line_x1, line_y - int(s * 0.025), line_w, line_y + int(s * 0.025)],
            radius=int(s * 0.02),
            fill=line_color
        )

    return img


# Generar .ico (Windows) con múltiples tamaños
sizes = [16, 32,48, 64, 128, 256]
images = [make_icon(s) for s in sizes]
images[0].save(
    "C:/Users/fabia/iCloudDrive/Documents/MisTareas/icon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes],
    append_images=images[1:]
)

# Guardar PNG 1024 (para .icns en Mac con iconutil)
make_icon(1024).save(
    "C:/Users/fabia/iCloudDrive/Documents/MisTareas/icon_1024.png",
    format="PNG"
)

print("Iconos generados: icon.ico y icon_1024.png")
