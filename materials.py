"""Material presets for icon transformation via gpt-image-2.

Each material defines:
  - id, label, emoji, swatch (CSS gradient): UI metadata
  - material_phrase: short concrete noun for "made of {phrase}"
  - details: lighting + texture cues following gpt-image-2 prompt guide
"""
from __future__ import annotations

MATERIALS: dict[str, dict] = {
    "gold": {
        "id": "gold",
        "label": "Or massif",
        "emoji": "\U0001F947",
        "swatch": "linear-gradient(135deg,#fde68a 0%,#f59e0b 50%,#92400e 100%)",
        "description": "Or 24 carats poli, finition miroir",
        "material_phrase": "polished 24-karat solid gold",
        "details": (
            "deep warm gold tone, mirror-like reflective surface, sharp specular highlights, "
            "subtle environmental reflections in warm amber, slight ambient occlusion at the edges, "
            "luxury jewelry finish"
        ),
    },
    "chrome": {
        "id": "chrome",
        "label": "Chrome",
        "emoji": "\U0001FA9E",
        "swatch": "linear-gradient(135deg,#f9fafb 0%,#9ca3af 50%,#1f2937 100%)",
        "description": "Chrome poli, finition miroir froide",
        "material_phrase": "polished chrome metal",
        "details": (
            "brilliant mirror finish, cool-toned specular highlights, "
            "subtle environmental reflections in soft blues and grays, "
            "high-gloss automotive paint shop quality"
        ),
    },
    "crystal": {
        "id": "crystal",
        "label": "Cristal",
        "emoji": "\U0001F48E",
        "swatch": "linear-gradient(135deg,#dbeafe 0%,#38bdf8 50%,#1e40af 100%)",
        "description": "Verre cristal transparent",
        "material_phrase": "transparent clear crystal glass",
        "details": (
            "refractive internal caustics, subtle prismatic light dispersion on the edges, "
            "smooth polished glossy surface, faint internal light scattering, "
            "faceted clarity, like a high-end paperweight"
        ),
    },
    "neon": {
        "id": "neon",
        "label": "Néon",
        "emoji": "\U0001F4A1",
        "swatch": "linear-gradient(135deg,#f0abfc 0%,#a855f7 50%,#22d3ee 100%)",
        "description": "Tube néon lumineux",
        "material_phrase": "glowing neon tube",
        "details": (
            "vivid hot magenta and electric cyan light emission along a hollow glass tube, "
            "soft outer halo glow around the shape, rounded tube ends, "
            "vibrant retro-futuristic signage aesthetic"
        ),
    },
    "wood": {
        "id": "wood",
        "label": "Bois sculpté",
        "emoji": "\U0001FAB5",
        "swatch": "linear-gradient(135deg,#fbbf24 0%,#a16207 50%,#451a03 100%)",
        "description": "Bois de noyer sculpté à la main",
        "material_phrase": "hand-carved solid walnut wood",
        "details": (
            "visible natural wood grain following the contours of the shape, "
            "warm matte finish with subtle beeswax sheen, fine tool marks revealing craftsmanship, "
            "rich warm brown wood tones"
        ),
    },
    "marble": {
        "id": "marble",
        "label": "Marbre",
        "emoji": "\U0001F3DB️",
        "swatch": "linear-gradient(135deg,#f9fafb 0%,#d1d5db 50%,#4b5563 100%)",
        "description": "Marbre de Carrare poli",
        "material_phrase": "polished white Carrara marble",
        "details": (
            "subtle organic grey veining, smooth glossy polished finish, "
            "classical sculpture aesthetic, soft directional studio lighting, "
            "fine natural stone texture"
        ),
    },
    "holographic": {
        "id": "holographic",
        "label": "Holographique",
        "emoji": "\U0001F308",
        "swatch": "linear-gradient(135deg,#c4b5fd 0%,#f0abfc 33%,#fbbf24 66%,#34d399 100%)",
        "description": "Foil holographique iridescent",
        "material_phrase": "iridescent holographic foil",
        "details": (
            "shifting rainbow gradient transitioning between cyan, magenta, gold and violet, "
            "metallic glossy sheen, smooth polished surface, "
            "prismatic refractive reflections, like Pokémon trading card foil"
        ),
    },
    "clay": {
        "id": "clay",
        "label": "Plasticine",
        "emoji": "\U0001F9F1",
        "swatch": "linear-gradient(135deg,#fda4af 0%,#ec4899 50%,#9d174d 100%)",
        "description": "Pâte à modeler colorée",
        "material_phrase": "soft modeling clay plasticine sculpture",
        "details": (
            "claymation aesthetic, subtle fingerprint and sculpting tool textures, "
            "vibrant matte coral color, soft rounded forms, handmade craft look, "
            "Aardman Animations style"
        ),
    },
    "paper": {
        "id": "paper",
        "label": "Papier découpé",
        "emoji": "\U0001F4C4",
        "swatch": "linear-gradient(135deg,#fef3c7 0%,#fb7185 50%,#be123c 100%)",
        "description": "Papier découpé multicouche",
        "material_phrase": "intricately layered cut paper craft",
        "details": (
            "multiple stacked colored paper layers in warm pastel tones, "
            "slight drop shadows between layers giving relief, "
            "matte textured paper fibers, delicate papercraft aesthetic"
        ),
    },
    "liquid_metal": {
        "id": "liquid_metal",
        "label": "Métal liquide",
        "emoji": "\U0001F30A",
        "swatch": "linear-gradient(135deg,#e5e7eb 0%,#64748b 50%,#0f172a 100%)",
        "description": "Mercure / chrome liquide",
        "material_phrase": "liquid mercury molten chrome",
        "details": (
            "smooth flowing molten metal surface, brilliant mirror finish with sharp specular reflections, "
            "fluid organic curves with slight viscous bulges, "
            "otherworldly metallic aesthetic, like a T-1000 surface"
        ),
    },
}


def build_prompt(material_id: str) -> str:
    """Construct the gpt-image-1.5 edit prompt for a given material.

    Follows the canonical structure from the prompt guide:
    intended use -> subject -> composition -> lighting -> background -> constraints.

    Critical: the output must have a fully transparent surround with NO shadow of any
    kind (drop, cast, contact, ground). The icon should appear to float in a void.
    """
    if material_id not in MATERIALS:
        raise ValueError(f"Unknown material id: {material_id}")
    m = MATERIALS[material_id]
    return (
        "Icon asset for a website UI — the output will be composited on any background color, "
        "so the icon must be perfectly cut out with NO shadow anywhere around it.\n"
        "INPUT description: the input image is a black icon silhouette centered on a pure white "
        "background. Use the input strictly as the reference SHAPE — keep the same subject and "
        "the same silhouette. Do NOT replace the subject with anything else, do NOT invent a new "
        "subject, do NOT add extra objects, bubbles, frames, badges, or scenery.\n"
        f"Subject: Re-render that exact icon shape as a 3D object made of {m['material_phrase']}. "
        f"{m['details']}.\n"
        "Composition: Preserve the EXACT same shape, proportions, and silhouette as the input. "
        "The icon is isolated, centered, occupies about 80% of the frame. "
        "Head-on square framing, no perspective distortion, no tilt.\n"
        "Lighting: Even diffuse studio lighting that reveals the material's surface from multiple sides. "
        "Form-revealing self-shading IS allowed on the icon itself (so the 3D volume reads). "
        "Specular highlights on the material surface are allowed.\n"
        "Background — STRICTLY ENFORCED: the WHITE input background must be completely REMOVED and "
        "REPLACED by FULLY TRANSPARENT pixels (alpha = 0). There is no floor, no plane, no ground, "
        "no surface beneath, behind or around the icon. The icon floats in pure transparent space. "
        "Do NOT keep any white area, do NOT add any colored area around the icon.\n"
        "Shadow constraints — STRICTLY ENFORCED:\n"
        "  - NO drop shadow under or behind the icon.\n"
        "  - NO cast shadow projected onto any surface.\n"
        "  - NO contact shadow at the base of the icon.\n"
        "  - NO soft halo, soft glow, or grey fade in the surrounding pixels (unless the material itself is a glowing neon).\n"
        "  - NO ambient-occlusion on a surface below the icon — only on the icon's own internal contours.\n"
        "  - Every pixel that is not part of the 3D icon material must be 100% transparent (alpha 0), "
        "not grey, not faded, not soft-shadowed, not tinted.\n"
        "Other constraints: No text, no labels, no logos, no watermark, no extra decorative elements, "
        "no frames, no circles, no bubbles, no folders, no other shapes besides the icon itself. "
        "Sharp clean edges where the material meets fully transparent pixels. "
        "Keep the exact silhouette of the input — do not alter the geometry. "
        "Original, non-infringing rendering."
    )
