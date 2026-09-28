"""Material and drawing-style presets for icon transformation via GPT Image.

Each material defines:
  - id, label, emoji, swatch (CSS gradient): UI metadata
  - material_phrase + details: lighting and texture for embossed materials
  - render_mode + style_reference: optional illustrated-style edit pipeline
"""
from __future__ import annotations

MATERIALS: dict[str, dict] = {
    "childlike_sketch": {
        "id": "childlike_sketch",
        "label": "Petit croquis enfantin",
        "emoji": "✏️",
        "swatch": "linear-gradient(135deg,#ffffff 0%,#f2f2f2 100%)",
        "description": "Feutre noir à main levée, contours irréguliers et quelques détails naïfs, sur fond transparent",
        "render_mode": "black_ink",
        "style_reference": "static/material-references/childlike_sketch.png",
    },
    "continuous_ribbon": {
        "id": "continuous_ribbon",
        "label": "Ruban continu",
        "emoji": "🎀",
        "swatch": "linear-gradient(135deg,#ff236c 0%,#ff236c 45%,#ff8a24 100%)",
        "description": "Un seul grand ruban plié en continu, avec des boucles et une extrémité libre",
        "render_mode": "continuous_ribbon",
        "style_reference": "static/material-references/continuous_ribbon.png",
    },
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
    "silver": {
        "id": "silver",
        "label": "Argent",
        "emoji": "\U0001F948",
        "swatch": "linear-gradient(135deg,#f8fafc 0%,#94a3b8 50%,#334155 100%)",
        "description": "Argent massif poli, finition satinée",
        "material_phrase": "polished sterling silver",
        "details": (
            "bright silvery-white tone with a barely-warm cast in the highlights, "
            "soft satin sheen, crisp specular highlights without harsh mirror reflections, "
            "fine jewelry finish, slightly softer and less blue than chrome"
        ),
    },
    "bronze": {
        "id": "bronze",
        "label": "Bronze",
        "emoji": "\U0001F949",
        "swatch": "linear-gradient(135deg,#fbbf24 0%,#b45309 50%,#451a03 100%)",
        "description": "Bronze poli, ton chaud cuivré",
        "material_phrase": "polished antique bronze",
        "details": (
            "warm coppery-brown tone with hints of orange and amber, "
            "subtle darker patina in the recesses, semi-polished cast-metal finish, "
            "softer specular highlights than gold, weighty foundry aesthetic"
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


def build_prompt(material_id: str, icon_label: str = "") -> str:
    """Construct the gpt-image-1.5 edit prompt for a given material.

    Follows the canonical structure from the prompt guide:
    intended use -> subject -> composition -> lighting -> background -> constraints.

    Critical: the output must have a fully transparent surround with NO shadow of any
    kind (drop, cast, contact, ground). The icon should appear to float in a void.

    icon_label: the Iconify icon name (e.g., "heat-pump", "horse"). Hyphens/underscores
    are converted to spaces. Used as a semantic anchor so the model doesn't
    reinterpret an ambiguous silhouette as something visually similar.
    """
    if material_id not in MATERIALS:
        raise ValueError(f"Unknown material id: {material_id}")
    m = MATERIALS[material_id]
    label = (icon_label or "").replace("-", " ").replace("_", " ").strip()
    label_hint = f" (the icon broadly represents \"{label}\")" if label else ""

    if m.get("render_mode") == "black_ink":
        return (
            "Redraw the subject of IMAGE 1 in the childlike BLACK felt-marker drawing style of IMAGE 2.\n"
            f"IMAGE 1 is the CONTENT reference{label_hint}: keep its recognizable subject, orientation "
            "and essential components. Its clean vector lines and exact proportions are NOT a style to copy. "
            "Simplify secondary details and freely make the outline crooked, uneven and hand-drawn.\n"
            "IMAGE 2 is ONLY the STYLE reference approved by the user: imitate its naive freehand character, "
            "broad black marker, irregular pressure, wobbly contours, little kinks, overlaps and untidy joins. "
            "Do NOT copy the subject, composition or subject-specific features from IMAGE 2 into the result.\n"
            "Imagine an EIGHT-YEAR-OLD proudly sketching the subject with a thick chisel-tip BLACK felt marker. "
            "Wrong but charming proportions, asymmetrical components, roughly drawn off-center inner features. "
            "The edges of every shape visibly wobble, with little kinks and line overlaps at turns, "
            "a few tiny transparent skips inside otherwise bold ink. Keep only essential inner features "
            "and at most TWO short interior accent strokes. Maintain the relaxed roughness of a child's "
            "notebook doodle, with very few details and broad soft strokes. It must look drawn by a child, "
            "not an adult designer creating a polished children's-book vector illustration.\n"
            "The childhood character is the PRIMARY style requirement. No tracing, no perfect Bezier curves, "
            "no immaculate constant-width computer lines, no symmetry, no geometric logo treatment. "
            "Center the complete subject, leave 12 percent empty margin, keep every mark inside the frame.\n"
            "Only pure BLACK ink. Flat two-dimensional marks. No colors, no white paint, no shading, "
            "no gradients, no hatching, no pencil, no 3D, no shadows, no text, no signature, no extra objects.\n"
            "True transparent RGBA background: NO PAPER and no white backdrop. Everything outside and "
            "INSIDE the outlined shapes must be alpha 0 except the actual black ink marks. Remove all "
            "white from IMAGE 1. Do not fill hollow shapes with white. Do not depict a checkerboard. "
            "Preserve the irregular ink edges and anti-aliasing."
        )

    if m.get("render_mode") == "continuous_ribbon":
        return (
            "Create a recognizable pictogram made by bending ONE SINGLE LONG CONTINUOUS RIBBON.\n"
            f"IMAGE 1 is the CONTENT reference{label_hint}: preserve the recognizable subject, "
            "overall silhouette, orientation and essential components. Reinterpret its geometry freely "
            "to make a graceful physically continuous ribbon construction. Do NOT trace or extrude "
            "the source's individual black regions.\n"
            "FIRST SIMPLIFY: reduce the reference to the few largest gestures needed to recognize it. "
            "Omit tiny isolated dots, date cells, grids, ticks and decorative details completely. "
            "A recognizable simplified one-line interpretation is required, not a detailed copy. "
            "An enclosed shape stays OPEN inside; do not create a solid panel and cut holes into it.\n"
            "IMAGE 2 is ONLY the STYLE reference: borrow its broad two-sided band, colors, soft folds "
            "and gentle depth. Never borrow its subject or subject-specific components. The construction "
            "rules below take priority over any disconnected pieces visible in a reference.\n"
            "CONSTRUCTION: imagine drawing the entire subject without lifting a pencil, then replacing "
            "that one continuous line with a WIDE FLAT RIBBON. Use exactly ONE unbranched strip of "
            "material from one end to the other, never several pieces. Its width stays substantial and "
            "mostly constant. It bends, curls, folds back on itself and passes above or below itself. "
            "Every component belongs to that same connected strip. At intersections show credible "
            "over-under overlaps, with visible continuation on both sides of each overlap. "
            "No glued junctions, branching paths, disconnected fins, floating accents or loose fragments.\n"
            "NEGATIVE SPACES: open holes arise naturally BETWEEN ribbon loops. They are not punched "
            "out of the ribbon. Do NOT cut, mask or end the band at boundaries of white areas in "
            "IMAGE 1. Connect separated source elements by a flowing return curve or an over-under "
            "bridge. You may cross some previously empty space, simplify minor details, enlarge loops "
            "and shift proportions to keep the whole subject flowing and recognizable. Continuity "
            "takes priority over pixel-perfect fidelity. The band has no internal holes or slots.\n"
            "FREE END: leave ONE conspicuous loose ribbon tail extending beyond the main pictogram "
            "by approximately 15 percent of its size, with a soft open curl and a plainly visible "
            "straight cut end. This tail must visibly grow from the same ribbon, not float separately. "
            "Place the other end discreetly near a fold. Exactly two physical ends in total. "
            "Do not turn the whole object into a gift bow.\n"
            "VISUAL STYLE: a broad soft matte ribbon, vivid warm fuchsia front and saturated mandarin "
            "orange reverse. Several generous folds and half-twists reveal both sides. Strong flowing "
            "gesture, expressive curves, elegant shallow spatial depth, soft self-shading at folds. "
            "A flat band with two distinct faces, not a rope, round tube, extruded outline or flat "
            "sticker. No metallic shine, fabric weave, paper grain or sharp origami creases.\n"
            "The ribbon is a NON-EMISSIVE, OPAQUE solid material: absolutely no luminous bloom, "
            "colored haze, reflected light in the surrounding void or translucent backing surface.\n"
            "COMPOSITION: straight-on view, centered on a square canvas, complete pictogram AND free "
            "tail inside the image with at least 12 percent empty margin. No cropping.\n"
            "OUTPUT: true transparent RGBA PNG. All surrounding space and gaps BETWEEN loops must "
            "have alpha zero. Remove the input backgrounds. No floor, cast shadow, external glow, "
            "white fill, background plate, checkerboard, text, watermark or unrelated decoration. "
            "Keep color and soft self-shading only on the ribbon itself."
        )

    input_block = (
        f"INPUT: a black silhouette icon centered on a pure white background{label_hint}.\n"
        "CRITICAL — STENCIL MODE: Treat the input as a LITERAL STENCIL. Every black region of "
        "the input must become a SHALLOWLY 3D-extruded solid in the output. Every white region "
        "must become fully transparent (alpha 0). Do NOT redraw the icon from your own generic "
        "concept of what the label means — render the EXACT geometric shapes that are visible "
        "in the input, pixel for pixel.\n"
        "OUTPUT STYLE — 2D PICTOGRAM, NOT FIGURATIVE SCULPTURE. The result must look like the "
        "original 2D pictogram has been EMBOSSED, LASER-CUT, or COOKIE-CUTTER-EXTRUDED out of "
        "the material — like a flat plaque or a 3D-printed logo plate. The shape's outline "
        "stays IDENTICAL to the input pictogram; only a small amount of depth perpendicular to "
        "the screen is added so the material's reflective properties read. DO NOT sculpt the "
        "icon into a figurative 3D object (no organic volume, no anatomy, no bulges, no "
        "rounded body, no realistic 3D rendering of the subject). Think \"embossed gold plaque "
        "of the icon\", not \"3D-printed figurine of the subject\".\n"
        "NEGATIVE SPACE — preserve ALL holes, gaps, and white areas between or inside the "
        "input's black strokes. Wherever the input has white pixels (the hole of an 'O', the "
        "gap between a frame and its inner detail, the spaces between detail lines, the "
        "background around a thin-stroked outline), the OUTPUT must have FULLY TRANSPARENT "
        "pixels (alpha 0) at the SAME locations. NEVER fill negative space with material. "
        "NEVER 'complete' or 'close' shapes that the input left open or hollow. If the input "
        "is a thin outline drawing (e.g. line-art with hollow center), the output must also "
        "be a thin outline of material, NOT a solid filled shape.\n"
        "PRESERVE ALL COMPONENTS — if the input contains an outer container (square, rectangle, "
        "rounded-square frame, circle) AND an inner detail (fan, dial, gauge, arrow, spokes, "
        "vents, segments, text, dots), the output MUST contain BOTH at the same relative scale "
        "and position. Do NOT keep only the most prominent sub-shape and discard the rest. "
        "Do NOT simplify or abstract the silhouette. Do NOT \"clean up\" the icon by removing "
        "frames, casings, backgrounds, or surrounding shapes that are part of the input.\n"
        "Do NOT replace the subject with anything else, do NOT invent a new subject, do NOT add "
        "extra objects, bubbles, frames, badges, rims, tires, halos, or scenery that aren't in "
        "the input.\n"
    )

    return (
        "Icon asset for a website UI — output must be a perfectly cut out PNG with NO shadow "
        "anywhere around it. The output is a 2D pictogram with shallow embossed depth, NOT a "
        "figurative 3D sculpture.\n"
        + input_block +
        f"MATERIAL: shallowly extrude every black region of the input into a solid plaque made "
        f"of {m['material_phrase']}. {m['details']}.\n"
        "Composition: Same shape, same proportions, same silhouette, same internal structure, "
        "same negative spaces as the input. The icon is isolated, centered, occupies about 80% "
        "of the frame. Head-on square framing, no perspective distortion, no tilt.\n"
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
