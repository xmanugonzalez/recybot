from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
SALIDA_COSTOS = BASE / 'recybot-costos.png'
SALIDA_FLUJO = BASE / 'recybot-flujo.png'
SALIDA_LAMINA = BASE / 'recybot-lamina-sistema-y-costos.png'
RENDER = BASE / 'recybot-render.png'

AZUL_OSCURO = '#0A2A4A'
AZUL = '#0878D1'
CIAN = '#16B7D8'
VERDE = '#20A464'
NARANJA = '#F29B38'
ROJO = '#D85B55'
GRIS = '#667788'
GRIS_CLARO = '#EAF2F8'
FONDO = '#DDECF8'
BLANCO = '#FFFFFF'


@dataclass(frozen=True)
class Costo:
    concepto: str
    monto: int
    fuente: str
    estado: str


COSTOS_ACTUALES = [
    Costo('Raspberry Pi 3 B+', 392_000, 'Nissei', 'Sistema actual'),
    Costo('Raspberry Pi 5 (8 GB)', 900_000, 'PYTECH', 'Sistema actual'),
    Costo('Cámara IMX219 / Arducam', 236_454, 'Yaxa Paraguay', 'Sistema actual'),
    Costo('Pantalla táctil de 7 pulgadas', 870_000, 'Electrónica Plett', 'Sistema actual'),
    Costo('2 tarjetas microSD', 150_000, 'Electrónica Plett', 'Sistema actual'),
    Costo('Fuentes, refrigeración y cables', 330_000, 'Estimación agrupada', 'Sistema actual'),
    Costo('Estructura y contenedores internos', 1_200_000, 'Estimación de fabricación', 'Sistema actual'),
]

COSTOS_PROPUESTOS = [
    Costo('Servo MG996R', 140_000, 'Electrónica Plett', 'Ampliación propuesta'),
    Costo('Sensor de proximidad E18-D80NK', 60_000, 'Electrónica Plett', 'Ampliación propuesta'),
    Costo('Controlador, fuente y cableado', 80_000, 'Estimación agrupada', 'Ampliación propuesta'),
]


def fuente(tamano: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    archivo = 'segoeuib.ttf' if negrita else 'segoeui.ttf'
    return ImageFont.truetype(str(Path('C:/Windows/Fonts') / archivo), tamano)


def gs(valor: int) -> str:
    return f"Gs. {valor:,.0f}".replace(',', '.')


def caja(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    relleno: str = BLANCO,
    borde: str = '#BED0DE',
    radio: int = 28,
    ancho: int = 3,
) -> None:
    draw.rounded_rectangle(xy, radius=radio, fill=relleno, outline=borde, width=ancho)


def texto_centrado(
    draw: ImageDraw.ImageDraw,
    centro_x: int,
    y: int,
    texto: str,
    font: ImageFont.FreeTypeFont,
    color: str,
) -> None:
    bbox = draw.textbbox((0, 0), texto, font=font)
    draw.text((centro_x - (bbox[2] - bbox[0]) / 2, y), texto, font=font, fill=color)


def parrafo(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    texto: str,
    font: ImageFont.FreeTypeFont,
    color: str,
    ancho_caracteres: int,
    espacio: int = 8,
) -> int:
    x, y = xy
    lineas = wrap(texto, width=ancho_caracteres, break_long_words=False)
    alto = font.size + espacio
    for linea in lineas:
        draw.text((x, y), linea, font=font, fill=color)
        y += alto
    return y


def flecha(draw: ImageDraw.ImageDraw, inicio: tuple[int, int], fin: tuple[int, int], color: str = AZUL) -> None:
    draw.line((inicio, fin), fill=color, width=7)
    x, y = fin
    draw.polygon([(x, y), (x - 18, y - 12), (x - 18, y + 12)], fill=color)


def icono_circulo(draw: ImageDraw.ImageDraw, centro: tuple[int, int], numero: str, color: str) -> None:
    x, y = centro
    draw.ellipse((x - 34, y - 34, x + 34, y + 34), fill=color)
    texto_centrado(draw, x, y - 23, numero, fuente(34, True), BLANCO)


def crear_costos() -> None:
    ancho, alto = 1600, 1200
    img = Image.new('RGB', (ancho, alto), BLANCO)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, ancho, 130), fill=AZUL_OSCURO)
    draw.text((75, 32), 'ANÁLISIS DE COSTOS DE RECYBOT', font=fuente(48, True), fill=BLANCO)
    draw.text((77, 92), 'Valores referenciales en guaraníes · consulta: 28/10/2026', font=fuente(23), fill='#CBE6FA')

    conceptos = COSTOS_ACTUALES + COSTOS_PROPUESTOS
    maximo = max(c.monto for c in conceptos)
    x_barra = 590
    ancho_barra = 760
    y = 165
    for costo in conceptos:
        propuesto = costo.estado == 'Ampliación propuesta'
        color = NARANJA if propuesto else AZUL
        draw.text((70, y + 7), costo.concepto, font=fuente(25, True), fill=AZUL_OSCURO)
        draw.text((70, y + 42), costo.fuente, font=fuente(19), fill=GRIS)
        draw.rounded_rectangle((x_barra, y, x_barra + ancho_barra, y + 48), radius=16, fill=GRIS_CLARO)
        longitud = max(18, int(ancho_barra * costo.monto / maximo))
        draw.rounded_rectangle((x_barra, y, x_barra + longitud, y + 48), radius=16, fill=color)
        draw.text((x_barra + ancho_barra + 25, y + 7), gs(costo.monto), font=fuente(24, True), fill=AZUL_OSCURO)
        y += 78

    total_actual = sum(c.monto for c in COSTOS_ACTUALES)
    ampliacion = sum(c.monto for c in COSTOS_PROPUESTOS)
    total = total_actual + ampliacion

    caja(draw, (55, 1055, 500, 1165), relleno='#E9F5FE', borde='#9DC9E8')
    draw.text((80, 1075), 'Sistema actual estimado', font=fuente(22), fill=GRIS)
    draw.text((80, 1110), gs(total_actual), font=fuente(31, True), fill=AZUL)
    caja(draw, (575, 1055, 1005, 1165), relleno='#FFF4E5', borde='#F4C27D')
    draw.text((600, 1075), 'Ampliación mecánica', font=fuente(22), fill=GRIS)
    draw.text((600, 1110), gs(ampliacion), font=fuente(31, True), fill=NARANJA)
    caja(draw, (1080, 1055, 1545, 1165), relleno='#E8F7EF', borde='#9BD3B6')
    draw.text((1105, 1075), 'Total proyectado', font=fuente(22), fill=GRIS)
    draw.text((1105, 1110), gs(total), font=fuente(31, True), fill=VERDE)
    img.save(SALIDA_COSTOS, quality=95)


def crear_flujo() -> None:
    ancho, alto = 1800, 720
    img = Image.new('RGB', (ancho, alto), '#F3F8FC')
    draw = ImageDraw.Draw(img)
    texto_centrado(draw, ancho // 2, 34, 'PROCESO REAL DE INTERACCIÓN CON RECYBOT', fuente(48, True), AZUL_OSCURO)
    texto_centrado(
        draw,
        ancho // 2,
        98,
        'El sistema actual detecta objetos; la persona confirma el material antes de guardar la muestra.',
        fuente(25),
        GRIS,
    )

    pasos = [
        ('1', 'CAPTURAR', 'La Pi 3 obtiene una fotografía nueva mediante la cámara.'),
        ('2', 'DETECTAR', 'La Pi 5 procesa la imagen con YOLOv8n y muestra los objetos encontrados.'),
        ('3', 'CONFIRMAR', 'El usuario selecciona: plástico, papel/cartón, metal u otros.'),
        ('4', 'REGISTRAR', 'La imagen confirmada queda disponible para revisión y entrenamiento.'),
    ]
    colores = [AZUL, CIAN, VERDE, NARANJA]
    margen = 65
    separacion = 32
    w = (ancho - margen * 2 - separacion * 3) // 4
    for i, ((numero, titulo, descripcion), color) in enumerate(zip(pasos, colores)):
        x = margen + i * (w + separacion)
        caja(draw, (x, 185, x + w, 600), borde='#C1D7E7', radio=34)
        icono_circulo(draw, (x + w // 2, 255), numero, color)
        texto_centrado(draw, x + w // 2, 320, titulo, fuente(31, True), AZUL_OSCURO)
        lineas = wrap(descripcion, width=31, break_long_words=False)
        yy = 385
        for linea in lineas:
            texto_centrado(draw, x + w // 2, yy, linea, fuente(24), GRIS)
            yy += 35
        if i < 3:
            flecha(draw, (x + w + 5, 390), (x + w + separacion - 7, 390), AZUL)

    caja(draw, (360, 630, 1440, 695), relleno='#FFF4E5', borde='#F4C27D', radio=24)
    texto_centrado(
        draw,
        ancho // 2,
        646,
        'Evolución propuesta: automatizar el desvío físico solo después de validar el modelo de materiales.',
        fuente(25, True),
        '#925B16',
    )
    img.save(SALIDA_FLUJO, quality=95)


def crear_lamina() -> None:
    ancho, alto = 1600, 2200
    img = Image.new('RGB', (ancho, alto), FONDO)
    draw = ImageDraw.Draw(img)

    texto_centrado(draw, ancho // 2, 32, 'SISTEMA PROPUESTO Y METAS DE VALIDACIÓN', fuente(51, True), AZUL_OSCURO)
    caja(draw, (45, 112, 1555, 330), radio=34)
    descripcion = (
        'Proyecto en ejecución: Recybot utiliza una Raspberry Pi 3 para capturar imágenes y servir la interfaz '
        'táctil, mientras una Raspberry Pi 5 ejecuta YOLOv8n. El desarrollo abarca la clasificación de residuos, '
        'la medición de llenado y el registro de los depósitos de prueba en el panel web.'
    )
    y = parrafo(draw, (95, 145), descripcion, fuente(27), AZUL_OSCURO, 103, 11)

    metas = [
        ('Precisión en 4 clases', '≥ 85 %'),
        ('Contenedores con medición de llenado', '3 de 3'),
        ('Depósitos de prueba registrados', '100 %'),
    ]
    posiciones = [120, 535, 1090]
    for (etiqueta, valor), x in zip(metas, posiciones):
        draw.ellipse((x, 282, x + 18, 300), fill=VERDE)
        draw.text((x + 28, 274), f'{etiqueta}: {valor}', font=fuente(23, True), fill=AZUL)

    caja(draw, (45, 365, 785, 1125), radio=34)
    texto_centrado(draw, 415, 395, 'COSTO ESTIMADO EN GUARANÍES', fuente(27, True), AZUL_OSCURO)

    grupos = [
        ('Cómputo', 1_292_000, AZUL),
        ('Interacción', 870_000, CIAN),
        ('Visión', 236_454, VERDE),
        ('Soporte eléctrico', 480_000, '#7E7AD8'),
        ('Estructura', 1_200_000, GRIS),
        ('Mecánica propuesta', 280_000, NARANJA),
    ]
    maximo = max(valor for _, valor, _ in grupos)
    base_y = 940
    x0 = 105
    bw = 78
    espacio = 30
    for i, (nombre, valor, color) in enumerate(grupos):
        bx = x0 + i * (bw + espacio)
        altura = int(410 * valor / maximo)
        draw.rounded_rectangle((bx, base_y - altura, bx + bw, base_y), radius=12, fill=color)
        texto_centrado(draw, bx + bw // 2, base_y - altura - 50, f'{valor / 1_000_000:.2f} M', fuente(20, True), AZUL_OSCURO)
        lineas = wrap(nombre, width=10)
        yy = base_y + 20
        for linea in lineas:
            texto_centrado(draw, bx + bw // 2, yy, linea, fuente(18), GRIS)
            yy += 25

    total_actual = sum(c.monto for c in COSTOS_ACTUALES)
    total_propuesto = total_actual + sum(c.monto for c in COSTOS_PROPUESTOS)
    draw.line((85, 1040, 745, 1040), fill='#D5E2EB', width=2)
    draw.text((90, 1055), f'Actual: {gs(total_actual)}', font=fuente(23, True), fill=AZUL)
    draw.text((430, 1055), f'Proyectado: {gs(total_propuesto)}', font=fuente(23, True), fill=VERDE)

    caja(draw, (815, 365, 1555, 1125), radio=34)
    texto_centrado(draw, 1185, 395, 'DISEÑO Y ARQUITECTURA DEL PROTOTIPO', fuente(27, True), AZUL_OSCURO)
    producto = Image.open(RENDER).convert('RGBA')
    producto.thumbnail((560, 575), Image.Resampling.LANCZOS)
    px = 1185 - producto.width // 2
    img.paste(producto, (px, 455), producto)
    caja(draw, (865, 990, 1505, 1090), relleno='#EDF7FD', borde='#B9D8EA', radio=22)
    texto_centrado(draw, 1185, 1008, 'Pi 3 + cámara  →  Pi 5 + YOLOv8n', fuente(24, True), AZUL)
    texto_centrado(draw, 1185, 1046, 'Interfaz Svelte 5 · cola local de aprendizaje', fuente(21), GRIS)

    caja(draw, (45, 1160, 1555, 1350), radio=28)
    draw.text((78, 1187), 'HALLAZGO CLAVE', font=fuente(27, True), fill=AZUL_OSCURO)
    texto_centrado(draw, ancho // 2, 1230, gs(total_propuesto), fuente(58, True), AZUL)
    texto_centrado(
        draw,
        ancho // 2,
        1300,
        'costo preliminar proyectado; la ampliación mecánica representa el 6,4 % del total',
        fuente(25),
        AZUL_OSCURO,
    )

    caja(draw, (45, 1385, 1555, 2095), radio=34)
    texto_centrado(draw, ancho // 2, 1415, 'PROCESO DE INTERACCIÓN VALIDADO EN EL SOFTWARE', fuente(35, True), AZUL_OSCURO)
    pasos = [
        ('1', 'CAPTURAR', 'Pi 3 y cámara'),
        ('2', 'DETECTAR', 'Pi 5 y YOLOv8n'),
        ('3', 'CONFIRMAR', 'Usuario elige material'),
        ('4', 'REGISTRAR', 'Muestra para revisión'),
    ]
    colores = [AZUL, CIAN, VERDE, NARANJA]
    x_inicio = 105
    w = 315
    gap = 62
    for i, ((numero, titulo, detalle), color) in enumerate(zip(pasos, colores)):
        x = x_inicio + i * (w + gap)
        caja(draw, (x, 1515, x + w, 1865), relleno='#F8FBFD', borde='#C7DCEB', radio=28)
        icono_circulo(draw, (x + w // 2, 1590), numero, color)
        texto_centrado(draw, x + w // 2, 1650, titulo, fuente(26, True), AZUL_OSCURO)
        for j, linea in enumerate(wrap(detalle, width=23)):
            texto_centrado(draw, x + w // 2, 1702 + j * 32, linea, fuente(22), GRIS)
        if i < 3:
            flecha(draw, (x + w + 9, 1695), (x + w + gap - 12, 1695), AZUL)

    caja(draw, (205, 1905, 1395, 2025), relleno='#FFF4E5', borde='#F4C27D', radio=24)
    texto_centrado(draw, ancho // 2, 1924, 'SIGUIENTE ETAPA PROPUESTA', fuente(23, True), '#925B16')
    texto_centrado(draw, ancho // 2, 1965, 'Entrenar el modelo por material y validar antes de accionar la compuerta.', fuente(25), '#925B16')

    nota = (
        'Fuentes de precios: Nissei, PYTECH, Yaxa Paraguay y Electrónica Plett. '
        'La estructura, el cableado y la fabricación son estimaciones y requieren cotización. '
        'Los valores pueden variar según disponibilidad.'
    )
    texto_centrado(draw, ancho // 2, 2130, nota, fuente(17), GRIS)
    img.save(SALIDA_LAMINA, quality=95)


def main() -> None:
    crear_costos()
    crear_flujo()
    crear_lamina()
    total_actual = sum(c.monto for c in COSTOS_ACTUALES)
    ampliacion = sum(c.monto for c in COSTOS_PROPUESTOS)
    total = total_actual + ampliacion
    print(f'Sistema actual: {gs(total_actual)}')
    print(f'Ampliación: {gs(ampliacion)}')
    print(f'Total proyectado: {gs(total)}')
    print(f'Participación de la ampliación: {ampliacion / total * 100:.1f}%')
    print(SALIDA_COSTOS)
    print(SALIDA_FLUJO)
    print(SALIDA_LAMINA)


if __name__ == '__main__':
    main()
