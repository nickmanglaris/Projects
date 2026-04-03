"""
AI-powered card image analyzer using Claude vision.
Evaluates raw card images against PSA 10 grading criteria.
"""
import asyncio
import base64
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PSA_PROMPT = """You are an expert PSA card grader. Analyze this sports card image and evaluate its PSA 10 potential.

PSA 10 GEM MINT criteria:
- Centering: Must be 60/40 or better on front, 75/25 or better on back
- Corners: Must be perfectly sharp with zero fraying or wear
- Edges: Must be clean with no nicks, chips, or roughness
- Surface: Must be free of scratches, print lines, stains, or loss of gloss

Based on what you can see in this image, respond in this EXACT format (no extra text):

CENTERING: [Excellent/Good/Poor] - [one sentence observation]
CORNERS: [Excellent/Good/Poor] - [one sentence observation]
EDGES: [Excellent/Good/Poor] - [one sentence observation]
SURFACE: [Excellent/Good/Poor] - [one sentence observation]
PSA10_POTENTIAL: [High/Medium/Low]
VERDICT: [2-3 sentence summary of whether this card is worth submitting to PSA and why]

If the image is too blurry, cropped, or low quality to assess, respond with:
PSA10_POTENTIAL: Unknown
VERDICT: Image quality insufficient for grading assessment."""


def _parse_analysis(text: str) -> dict:
    """Parse Claude's structured response into a dict."""
    result = {
        "centering": None,
        "corners": None,
        "edges": None,
        "surface": None,
        "psa10_potential": "Unknown",
        "verdict": text.strip(),
    }

    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("CENTERING:"):
            result["centering"] = line.replace("CENTERING:", "").strip()
        elif line.startswith("CORNERS:"):
            result["corners"] = line.replace("CORNERS:", "").strip()
        elif line.startswith("EDGES:"):
            result["edges"] = line.replace("EDGES:", "").strip()
        elif line.startswith("SURFACE:"):
            result["surface"] = line.replace("SURFACE:", "").strip()
        elif line.startswith("PSA10_POTENTIAL:"):
            result["psa10_potential"] = line.replace("PSA10_POTENTIAL:", "").strip()
        elif line.startswith("VERDICT:"):
            result["verdict"] = line.replace("VERDICT:", "").strip()

    return result


def _potential_score(potential: str) -> int:
    return {"High": 3, "Medium": 2, "Low": 1}.get(potential, 0)


async def analyze_card_image(image_url: str, api_key: str) -> dict:
    """Download a card image and analyze it with Claude vision."""
    if not image_url:
        return {"psa10_potential": "Unknown", "verdict": "No image available for this listing."}

    # Download image
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(image_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200 or not resp.content:
                return {"psa10_potential": "Unknown", "verdict": "Could not load card image."}
            image_data = base64.standard_b64encode(resp.content).decode("utf-8")
            content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
    except Exception as e:
        logger.warning(f"Image download failed for {image_url}: {e}")
        return {"psa10_potential": "Unknown", "verdict": "Could not load card image."}

    # Analyze with Claude
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": PSA_PROMPT},
                    ],
                }
            ],
        )
        return _parse_analysis(message.content[0].text)
    except Exception as e:
        logger.error(f"Claude analysis error: {e}")
        return {"psa10_potential": "Unknown", "verdict": f"AI analysis unavailable: {str(e)}"}


async def analyze_listings(listings: list[dict], api_key: str, max_analyze: int = 15) -> list[dict]:
    """Analyze multiple card listings and sort by PSA 10 potential."""
    if not api_key or api_key in ("", "YOUR_ANTHROPIC_API_KEY_HERE"):
        # No API key — return listings without analysis
        for listing in listings:
            listing["analysis"] = {
                "psa10_potential": "Not analyzed",
                "verdict": "Add your ANTHROPIC_API_KEY to backend/.env to enable AI grading analysis.",
            }
        return listings

    # Analyze up to max_analyze listings concurrently (in batches to avoid rate limits)
    to_analyze = listings[:max_analyze]
    batch_size = 5

    for i in range(0, len(to_analyze), batch_size):
        batch = to_analyze[i:i + batch_size]
        tasks = [analyze_card_image(item.get("image_url", ""), api_key) for item in batch]
        analyses = await asyncio.gather(*tasks, return_exceptions=True)

        for item, analysis in zip(batch, analyses):
            if isinstance(analysis, Exception):
                item["analysis"] = {"psa10_potential": "Unknown", "verdict": "Analysis failed."}
            else:
                item["analysis"] = analysis

        if i + batch_size < len(to_analyze):
            await asyncio.sleep(1)  # Brief pause between batches

    # Fill remaining listings without analysis
    for listing in listings[max_analyze:]:
        listing["analysis"] = {"psa10_potential": "Not analyzed", "verdict": "Limit reached."}

    # Sort: High potential first, then Medium, then Low/Unknown
    listings.sort(key=lambda x: _potential_score(x.get("analysis", {}).get("psa10_potential", "")), reverse=True)
    return listings
