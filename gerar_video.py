import asyncio
import math
import os
import subprocess
import wave
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LARGURA, ALTURA = 1280, 720
FPS = 24
SAMPLE_RATE = 44100

# Voz de IA masculina bem calma e natural
VOZ_NARRADOR = "pt-BR-AntonioNeural"

ROTEIRO = [
    {
        "cena": "abertura",
        "texto": "Se você visse alguém caído na estrada hoje... você pararia, ou fingiria que não viu? Que a paz de Deus esteja com você. Bem-vindo ao Tempo Diário.",
    },
    {
        "cena": "ataque",
        "texto": "Na Bíblia, um homem estava caminhando sozinho pela rua... quando de repente foi cercado, agredido, e deixado caído no chão.",
    },
    {
        "cena": "ignorando",
        "texto": "Logo depois, um monte de pessoas passou por ali... inclusive gente religiosa e importante. Eles olharam para ele, mas viraram o rosto e seguiram adiante, sem ajudar.",
    },
    {
        "cena": "samaritano",
        "texto": "Até que um samaritano, alguém de quem ninguém esperava nada, parou. Ele sentiu compaixão, cuidou das feridas daquele homem e o levou para um lugar seguro.",
    },
    {
        "cena": "final",
        "texto": "O recado de Deus para o seu dia hoje é simples: amor não é só sentimento, é atitude. Não passe direto pela dor de ninguém. Que Deus te abençoe e te use hoje. Tenha um excelente dia.",
    },
]


async def sintetizar_falas():
    for i, item in enumerate(ROTEIRO):
        mp3_path = f"temp_fala_{i}.mp3"
        for tentativa in range(3):
            try:
                comunicador = edge_tts.Communicate(
                    item["texto"], VOZ_NARRADOR, rate="-4%", pitch="-1Hz"
                )
                await comunicador.save(mp3_path)
                break
            except Exception as e:
                if tentativa == 2:
                    raise e
                await asyncio.sleep(2)


def mp3_para_array(mp3_path, wav_path):
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", mp3_path,
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "wav", wav_path
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with wave.open(wav_path, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def carregar_fonte(tamanho, negrito=False):
    caminhos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for c in caminhos:
        if os.path.exists(c):
            return ImageFont.truetype(c, tamanho)
    return ImageFont.load_default()


def quebrar_texto(draw, texto, fonte, largura_max):
    palavras = texto.split()
    linhas = []
    atual = ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        bbox = draw.textbbox((0, 0), teste, font=fonte)
        if (bbox[2] - bbox[0]) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def criar_cenario_rua():
    img = Image.new("RGB", (LARGURA, ALTURA))
    draw = ImageDraw.Draw(img)

    # Céu calmo de entardecer
    for y in range(470):
        r = int(28 + (102 - 28) * (y / 470))
        g = int(34 + (82 - 34) * (y / 470))
        b = int(68 + (122 - 68) * (y / 470))
        draw.line([(0, y), (LARGURA, y)], fill=(r, g, b))

    # Casinhas e árvores simples no fundo da rua
    predios = [
        (50, 290, 170, 470, (44, 48, 72)),
        (190, 250, 320, 470, (38, 42, 65)),
        (360, 310, 480, 470, (48, 52, 76)),
        (780, 270, 920, 470, (40, 44, 68)),
        (950, 300, 1080, 470, (46, 50, 74)),
        (1110, 260, 1230, 470, (36, 40, 62)),
    ]
    for x1, y1, x2, y2, cor in predios:
        draw.rectangle([x1, y1, x2, y2], fill=cor)
        for wy in range(y1 + 25, y2 - 30, 38):
            for wx in range(x1 + 20, x2 - 25, 36):
                draw.rectangle([wx, wy, wx + 16, wy + 20], fill=(225, 195, 130))

    # Postes de luz na calçada
    for px in (280, 640, 1000):
        draw.rectangle([px - 4, 240, px + 4, 470], fill=(55, 58, 78))
        draw.ellipse([px - 18, 224, px + 18, 256], fill=(255, 226, 150))

    # Calçada e rua
    draw.rectangle([0, 465, LARGURA, 525], fill=(82, 86, 105))
    draw.line([(0, 465), (LARGURA, 465)], fill=(55, 58, 75), width=4)
    draw.rectangle([0, 525, LARGURA, ALTURA], fill=(42, 46, 60))
    for lx in range(30, LARGURA, 120):
        draw.rectangle([lx, 590, lx + 60, 600], fill=(120, 124, 140))

    return img


def desenhar_bonequinho(
    draw, cx, cy, cor_roupa, cor_pele, cor_cabelo,
    escala=1.0, andando=False, falando=False, boca=0.0,
    piscando=False, tempo=0.0, direcao=1, bravo=False,
    chapeu=None, ferido=False, virando_rosto=False
):
    borda = (30, 30, 42)
    w_borda = max(3, int(4 * escala))
    r = int(52 * escala)

    passo = math.sin(tempo * 14.0) if andando else 0.0
    balanco = abs(math.sin(tempo * 14.0)) * 5.0 * escala if andando else (math.sin(tempo * 7.0) * 3.0 * escala if falando else 0.0)
    cy = int(cy - balanco)

    # Sombra
    draw.ellipse([cx - int(45 * escala), cy + int(90 * escala), cx + int(45 * escala), cy + int(106 * escala)], fill=(28, 30, 42))

    # Pezinhos
    pe1_x = cx - int(18 * escala) + int(passo * 16 * escala)
    pe2_x = cx + int(18 * escala) - int(passo * 16 * escala)
    pe_y = cy + int(88 * escala)
    draw.ellipse([pe1_x - int(13 * escala), pe_y - int(8 * escala), pe1_x + int(13 * escala), pe_y + int(10 * escala)], fill=(45, 45, 58), outline=borda, width=w_borda)
    draw.ellipse([pe2_x - int(13 * escala), pe_y - int(8 * escala), pe2_x + int(13 * escala), pe_y + int(10 * escala)], fill=(45, 45, 58), outline=borda, width=w_borda)

    # Corpinho redondinho
    draw.ellipse([cx - int(42 * escala), cy + int(24 * escala), cx + int(42 * escala), cy + int(92 * escala)], fill=cor_roupa, outline=borda, width=w_borda)

    # Mãozinhas
    mao_swing = int(passo * 14 * escala)
    draw.ellipse([cx - int(48 * escala) - mao_swing, cy + int(48 * escala), cx - int(30 * escala) - mao_swing, cy + int(66 * escala)], fill=cor_pele, outline=borda, width=w_borda)
    draw.ellipse([cx + int(30 * escala) + mao_swing, cy + int(48 * escala), cx + int(48 * escala) + mao_swing, cy + int(66 * escala)], fill=cor_pele, outline=borda, width=w_borda)

    # Cabeça redondinha
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor_pele, outline=borda, width=w_borda)

    # Cabelo ou chapéu
    draw.chord([cx - r, cy - r - 2, cx + r, cy - int(6 * escala)], start=185, end=355, fill=cor_cabelo, outline=borda, width=w_borda)
    if chapeu == "cartola":
        draw.rectangle([cx - int(38 * escala), cy - r - int(6 * escala), cx + int(38 * escala), cy - r + int(4 * escala)], fill=(35, 35, 48), outline=borda, width=3)
        draw.rectangle([cx - int(24 * escala), cy - r - int(34 * escala), cx + int(24 * escala), cy - r - int(4 * escala)], fill=(35, 35, 48), outline=borda, width=3)
    elif chapeu == "religioso":
        draw.ellipse([cx - int(36 * escala), cy - r - int(18 * escala), cx + int(36 * escala), cy - r + int(10 * escala)], fill=(235, 225, 200), outline=borda, width=3)

    # Deslocamento dos olhos se estiver olhando pro lado/virando o rosto
    olhar_x = int(12 * escala * direcao) if not virando_rosto else int(-14 * escala * direcao)

    # Olhos
    for ox_base in (cx - int(18 * escala), cx + int(18 * escala)):
        ox = ox_base + int(olhar_x * 0.4)
        oy = cy - int(6 * escala)
        if piscando:
            draw.line([(ox - int(7 * escala), oy), (ox + int(7 * escala), oy)], fill=borda, width=w_borda)
        else:
            er = int(8 * escala)
            draw.ellipse([ox - er, oy - int(10 * escala), ox + er, oy + int(10 * escala)], fill=(255, 255, 255), outline=borda, width=max(2, w_borda - 1))
            pr = int(4 * escala)
            draw.ellipse([ox - pr + int(olhar_x * 0.15), oy - pr, ox + pr + int(olhar_x * 0.15), oy + pr], fill=borda)

        # Sobrancelha brava para agressores
        if bravo:
            sinal = 1 if ox_base < cx else -1
            draw.line(
                [(ox - int(10 * escala), oy - int(14 * escala) - sinal * 4),
                 (ox + int(10 * escala), oy - int(14 * escala) + sinal * 4)],
                fill=borda, width=w_borda
            )

    # Curativo se ferido
    if ferido:
        draw.rounded_rectangle([cx + int(16 * escala), cy + int(8 * escala), cx + int(38 * escala), cy + int(20 * escala)], radius=3, fill=(245, 232, 210), outline=borda, width=2)

    # Boca
    by = cy + int(20 * escala) + int(olhar_x * 0.05)
    bx = cx + int(olhar_x * 0.3)
    if falando and boca > 0.08:
        ab = int((4 + min(boca, 1.0) * 14) * escala)
        draw.ellipse([bx - int(10 * escala), by - ab // 2, bx + int(10 * escala), by + ab], fill=(165, 68, 78), outline=borda, width=max(2, w_borda - 1))
    elif bravo:
        draw.arc([bx - int(10 * escala), by, bx + int(10 * escala), by + int(12 * escala)], start=195, end=345, fill=borda, width=max(2, w_borda - 1))
    elif virando_rosto:
        draw.line([(bx - int(8 * escala), by + 4), (bx + int(8 * escala), by + 4)], fill=borda, width=max(2, w_borda - 1))
    else:
        draw.arc([bx - int(10 * escala), by - 4, bx + int(10 * escala), by + int(8 * escala)], start=15, end=165, fill=borda, width=max(2, w_borda - 1))


def desenhar_caido(draw, cx, cy, escala=1.0, ferido=True):
    borda = (30, 30, 42)
    w = max(3, int(4 * escala))
    r = int(46 * escala)

    # Sombra no chão
    draw.ellipse([cx - int(95 * escala), cy + int(20 * escala), cx + int(85 * escala), cy + int(42 * escala)], fill=(25, 27, 38))

    # Corpo deitado na horizontal
    draw.ellipse([cx - int(80 * escala), cy - int(22 * escala), cx + int(15 * escala), cy + int(34 * escala)], fill=(107, 163, 214), outline=borda, width=w)
    # Pezinhos
    draw.ellipse([cx - int(96 * escala), cy - int(10 * escala), cx - int(74 * escala), cy + int(14 * escala)], fill=(45, 45, 58), outline=borda, width=w)
    draw.ellipse([cx - int(92 * escala), cy + int(10 * escala), cx - int(70 * escala), cy + int(34 * escala)], fill=(45, 45, 58), outline=borda, width=w)

    # Cabeça
    hx = cx + int(45 * escala)
    hy = cy - int(8 * escala)
    draw.ellipse([hx - r, hy - r, hx + r, hy + r], fill=(255, 224, 189), outline=borda, width=w)
    draw.chord([hx - r, hy - r, hx + r, hy - int(4 * escala)], start=185, end=355, fill=(61, 52, 74), outline=borda, width=w)

    # Olhos fechados de dor (> <)
    for ox in (hx - int(16 * escala), hx + int(14 * escala)):
        oy = hy - int(4 * escala)
        draw.line([(ox - 6, oy - 5), (ox + 6, oy), (ox - 6, oy + 5)], fill=borda, width=3)

    # Boca triste
    draw.arc([hx - 10, hy + 14, hx + 10, hy + 26], start=195, end=345, fill=borda, width=3)

    if ferido:
        draw.rounded_rectangle([hx - 28, hy + 6, hx - 6, hy + 17], radius=3, fill=(245, 232, 210), outline=borda, width=2)


def desenhar_impacto_rapido(draw, cx, cy, t, fonte):
    # Nuvem rápida de briga estilo desenho animado
    raios = 10
    pontos = []
    for k in range(raios * 2):
        ang = k * math.pi / raios + t * 8.0
        dist = 105 if k % 2 == 0 else 65
        pontos.append((cx + math.cos(ang) * dist, cy + math.sin(ang) * dist * 0.75))
    draw.polygon(pontos, fill=(255, 235, 130), outline=(220, 75, 55), width=4)
    texto = "PÁ!" if int(t * 10) % 2 == 0 else "POW!"
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, cy - 22), texto, font=fonte, fill=(200, 40, 35))


def desenhar_coracao(draw, cx, cy, tam=18):
    draw.ellipse([cx - tam, cy - tam // 2, cx, cy + tam // 2], fill=(240, 85, 105))
    draw.ellipse([cx, cy - tam // 2, cx + tam, cy + tam // 2], fill=(240, 85, 105))
    draw.polygon([(cx - tam, cy), (cx + tam, cy), (cx, cy + int(tam * 1.25))], fill=(240, 85, 105))


def main():
    print("1. Gerando voz neural calma...")
    asyncio.run(sintetizar_falas())

    pausa_inicial = int(SAMPLE_RATE * 0.35)
    pausa_entre = int(SAMPLE_RATE * 0.35)
    pausa_final = int(SAMPLE_RATE * 1.0)

    partes_audio = [np.zeros(pausa_inicial, dtype=np.float32)]
    segmentos = []
    pos_atual = pausa_inicial

    for i, item in enumerate(ROTEIRO):
        mp3_path = f"temp_fala_{i}.mp3"
        wav_path = f"temp_fala_{i}.wav"
        arr = mp3_para_array(mp3_path, wav_path)

        segmentos.append({
            "inicio": pos_atual / SAMPLE_RATE,
            "fim": (pos_atual + len(arr)) / SAMPLE_RATE,
            "cena": item["cena"],
            "texto": item["texto"],
        })

        partes_audio.append(arr)
        pos_atual += len(arr)

        if i < len(ROTEIRO) - 1:
            partes_audio.append(np.zeros(pausa_entre, dtype=np.float32))
            pos_atual += pausa_entre

    partes_audio.append(np.zeros(pausa_final, dtype=np.float32))
    voz_completa = np.concatenate(partes_audio)

    pico = np.max(np.abs(voz_completa))
    if pico > 0:
        voz_completa = (voz_completa / pico) * 0.90

    audio_final = np.clip(voz_completa, -0.98, 0.98)

    with wave.open("temp_audio_final.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio_final * 32767.0).astype(np.int16).tobytes())

    duracao_total = len(audio_final) / SAMPLE_RATE
    total_frames = int(math.ceil(duracao_total * FPS))
    print(f"2. Renderizando {total_frames} frames ({duracao_total:.1f}s)...")

    cenario = criar_cenario_rua()
    fonte_legenda = carregar_fonte(27, negrito=True)
    fonte_canal = carregar_fonte(20, negrito=True)
    fonte_impacto = carregar_fonte(34, negrito=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{LARGURA}x{ALTURA}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", "temp_audio_final.wav",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        "video.mp4",
    ]
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    amostras_por_frame = SAMPLE_RATE // FPS

    multidao = [
        {"offset": 0.00, "dir": 1, "roupa": (175, 165, 195), "chapeu": "religioso"},
        {"offset": 0.14, "dir": -1, "roupa": (75, 85, 110), "chapeu": "cartola"},
        {"offset": 0.28, "dir": 1, "roupa": (195, 125, 110), "chapeu": None},
        {"offset": 0.42, "dir": -1, "roupa": (115, 155, 130), "chapeu": None},
        {"offset": 0.56, "dir": 1, "roupa": (160, 140, 105), "chapeu": "cartola"},
        {"offset": 0.70, "dir": -1, "roupa": (130, 115, 165), "chapeu": None},
    ]

    for frame_idx in range(total_frames):
        t = frame_idx / FPS
        frame = cenario.copy()
        draw = ImageDraw.Draw(frame)

        seg_atual = segmentos[-1]
        for seg in segmentos:
            if seg["inicio"] <= t <= seg["fim"]:
                seg_atual = seg
                break

        dur_seg = max(0.1, seg_atual["fim"] - seg_atual["inicio"])
        prog = max(0.0, min(1.0, (t - seg_atual["inicio"]) / dur_seg))

        a_ini = int(t * SAMPLE_RATE)
        a_fim = min(a_ini + amostras_por_frame, len(voz_completa))
        rms = float(np.sqrt(np.mean(voz_completa[a_ini:a_fim] ** 2))) if a_fim > a_ini else 0.0
        boca = min(rms * 5.2, 1.0)
        piscando = (t % 3.6) < 0.14

        cena = seg_atual["cena"]

        if cena == "abertura":
            cx = int(280 + prog * 360)
            desenhar_bonequinho(
                draw, cx, 390, (107, 163, 214), (255, 224, 189), (61, 52, 74),
                escala=1.2, andando=True, falando=True, boca=boca, piscando=piscando, tempo=t
            )

        elif cena == "ataque":
            # Cena RÁPIDA: anda -> 2 caras cercam e batem rápido -> cai no chão
            if prog < 0.30:
                p_sub = prog / 0.30
                cx = int(220 + p_sub * 320)
                desenhar_bonequinho(
                    draw, cx, 405, (107, 163, 214), (255, 224, 189), (61, 52, 74),
                    escala=1.0, andando=True, piscando=piscando, tempo=t
                )
                # Agressores surgindo rápido pela direita
                ag1_x = int(1240 - p_sub * 540)
                ag2_x = int(1320 - p_sub * 540)
                desenhar_bonequinho(draw, ag1_x, 405, (65, 58, 80), (235, 195, 165), (30, 30, 38), andando=True, direcao=-1, bravo=True, tempo=t * 1.4)
                desenhar_bonequinho(draw, ag2_x, 412, (82, 50, 56), (220, 180, 150), (30, 30, 38), andando=True, direcao=-1, bravo=True, tempo=t * 1.4)

            elif prog < 0.68:
                # Pancadaria rápida no centro!
                shake = int(math.sin(t * 55) * 14)
                desenhar_bonequinho(draw, 540 + shake, 408, (107, 163, 214), (255, 224, 189), (61, 52, 74), ferido=True, tempo=t)
                desenhar_bonequinho(draw, 465 - shake, 404, (65, 58, 80), (235, 195, 165), (30, 30, 38), direcao=1, bravo=True, tempo=t * 1.6)
                desenhar_bonequinho(draw, 625 + shake, 404, (82, 50, 56), (220, 180, 150), (30, 30, 38), direcao=-1, bravo=True, tempo=t * 1.6)
                desenhar_impacto_rapido(draw, 545, 365, t, fonte_impacto)

            else:
                # Ele caído e os agressores fogem correndo rápido
                p_fuga = (prog - 0.68) / 0.32
                desenhar_caido(draw, 530, 470, escala=1.0, ferido=True)
                desenhar_bonequinho(draw, int(680 + p_fuga * 660), 405, (65, 58, 80), (235, 195, 165), (30, 30, 38), andando=True, bravo=True, tempo=t * 1.7)
                desenhar_bonequinho(draw, int(760 + p_fuga * 680), 412, (82, 50, 56), (220, 180, 150), (30, 30, 38), andando=True, bravo=True, tempo=t * 1.7)

        elif cena == "ignorando":
            # Homem caído no meio e UM MONTE de pessoas passando direto sem ajudar
            desenhar_caido(draw, 560, 475, escala=1.0, ferido=True)
            for m in multidao:
                p_loc = (prog - m["offset"]) / 0.38
                if 0.0 <= p_loc <= 1.0:
                    if m["dir"] == 1:
                        mx = int(-80 + p_loc * 1440)
                    else:
                        mx = int(1360 - p_loc * 1440)
                    perto = abs(mx - 560) < 190
                    desenhar_bonequinho(
                        draw, mx, 402, m["roupa"], (248, 215, 190), (65, 52, 48),
                        andando=True, direcao=m["dir"], chapeu=m["chapeu"],
                        virando_rosto=perto, piscando=piscando, tempo=t * 1.15
                    )

        elif cena == "samaritano":
            if prog < 0.35:
                p_sub = prog / 0.35
                desenhar_caido(draw, 560, 475, escala=1.0, ferido=True)
                sx = int(1240 - p_sub * 530)
                desenhar_bonequinho(
                    draw, sx, 405, (230, 185, 110), (242, 204, 175), (72, 56, 44),
                    andando=True, direcao=-1, piscando=piscando, tempo=t
                )
            elif prog < 0.72:
                desenhar_caido(draw, 560, 475, escala=1.0, ferido=True)
                desenhar_bonequinho(
                    draw, 700, 420, (230, 185, 110), (242, 204, 175), (72, 56, 44),
                    andando=False, direcao=-1, piscando=piscando, tempo=t
                )
                desenhar_coracao(draw, 635, 315 + int(math.sin(t * 5) * 6), tam=18)
            else:
                # Ajudado, levanta e vão embora juntos
                p_sub = (prog - 0.72) / 0.28
                dx = int(p_sub * 260)
                desenhar_bonequinho(
                    draw, 550 + dx, 405, (107, 163, 214), (255, 224, 189), (61, 52, 74),
                    andando=True, ferido=True, piscando=piscando, tempo=t
                )
                desenhar_bonequinho(
                    draw, 680 + dx, 405, (230, 185, 110), (242, 204, 175), (72, 56, 44),
                    andando=True, direcao=1, piscando=piscando, tempo=t
                )
                desenhar_coracao(draw, 615 + dx, 290, tam=16)

        else:
            # Cena final: narrador fechando a mensagem com calma
            desenhar_bonequinho(
                draw, 640, 390, (107, 163, 214), (255, 224, 189), (61, 52, 74),
                escala=1.25, falando=True, boca=boca, piscando=piscando, tempo=t
            )
            desenhar_coracao(draw, 640, 225 + int(math.sin(t * 4) * 5), tam=16)

        # Overlay do selo do canal e legenda
        frame_rgba = frame.convert("RGBA")
        ov = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(ov)

        ov_draw.rounded_rectangle([32, 24, 315, 64], radius=20, fill=(20, 22, 36, 165))
        ov_draw.text((52, 33), "Tempo Diário  •  @tempodiario", font=fonte_canal, fill=(255, 224, 170, 240))

        linhas = quebrar_texto(ov_draw, seg_atual["texto"], fonte_legenda, 1080)
        alt_linha = 36
        alt_caixa = len(linhas) * alt_linha + 26
        y_topo = ALTURA - alt_caixa - 20

        ov_draw.rounded_rectangle([70, y_topo, LARGURA - 70, ALTURA - 20], radius=20, fill=(18, 20, 34, 195))
        for idx_l, linha in enumerate(linhas):
            bbox = ov_draw.textbbox((0, 0), linha, font=fonte_legenda)
            larg_l = bbox[2] - bbox[0]
            x_l = (LARGURA - larg_l) // 2
            y_l = y_topo + 13 + idx_l * alt_linha
            ov_draw.text((x_l, y_l), linha, font=fonte_legenda, fill=(255, 255, 255, 245))

        frame = Image.alpha_composite(frame_rgba, ov).convert("RGB")
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()

    for f in os.listdir("."):
        if f.startswith("temp_"):
            os.remove(f)
    print("3. Vídeo video.mp4 gerado com sucesso!")


if __name__ == "__main__":
    main()
