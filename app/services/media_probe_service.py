import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict


class MediaProbeService:
    @classmethod
    async def probe(cls: type['MediaProbeService'], path: Path) -> Dict[str, Any]:
        return await asyncio.to_thread(cls._probe, path)

    @classmethod
    def _probe(cls: type['MediaProbeService'], path: Path) -> Dict[str, Any]:
        command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration:stream=codec_type,width,height',
            '-of', 'json',
            str(path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    @classmethod
    async def duration_seconds(cls: type['MediaProbeService'], path: Path) -> int:
        data = await cls.probe(path)
        duration = float(data.get('format', {}).get('duration') or 0)
        return int(duration + 0.999)
