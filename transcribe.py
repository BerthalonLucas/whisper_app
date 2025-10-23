import os
import sys
from faster_whisper import WhisperModel

# Désactiver les avertissements de symlinks pour Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

def transcribe_audio(audio_file):
    """Transcrit un fichier audio avec Whisper large-v3"""

    # Vérifier que le fichier existe
    if not os.path.exists(audio_file):
        print(f"❌ Erreur: Le fichier '{audio_file}' n'existe pas")
        return

    print(f"📂 Fichier: {audio_file}")

    # Détection GPU
    try:
        import ctranslate2
        has_gpu = ctranslate2.get_cuda_device_count() > 0
    except:
        has_gpu = False

    device = "cuda" if has_gpu else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    print(f"⚙️  Initialisation du modèle Whisper large-v3 sur {device}...")

    # Charger le modèle
    model = WhisperModel(
        "large-v3",
        device=device,
        compute_type=compute_type,
        cpu_threads=4
    )

    print("🔄 Transcription en cours...")

    # Transcrire
    segments, info = model.transcribe(
        audio_file,
        language=None,  # Détection automatique
        task="transcribe",
        vad_filter=False,  # Désactivé pour transcrire l'intégralité du fichier
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    )

    # Récupérer le texte en convertissant le générateur en liste
    print("📥 Récupération des segments...")
    segments_list = list(segments)
    print(f"🔢 Nombre de segments trouvés: {len(segments_list)}")

    transcription = ""
    for segment in segments_list:
        transcription += segment.text + " "

    transcription = transcription.strip()

    if transcription:
        print(f"\n✅ Langue détectée: {info.language}")
        print(f"📝 Transcription:\n{transcription}")
    else:
        print("❌ Aucune parole détectée")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <fichier_audio>")
        print("Exemple: python transcribe.py audio.wav")
        sys.exit(1)

    audio_file = sys.argv[1]
    transcribe_audio(audio_file)
