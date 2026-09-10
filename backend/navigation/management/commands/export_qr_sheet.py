"""
Generates a printable HTML sheet of outdoor QR codes (scan → locate workflow).

    python manage.py export_qr_sheet
    python manage.py export_qr_sheet --output qr_codes/outdoor_qr_sheet.html
    python manage.py export_qr_sheet --only MAIN_GATE EIGHTH_BLOCK_ENTRANCE

Images are served live by GET /api/qr/outdoor/<node_id>/ so the sheet never
embeds stale codes; each card also prints the raw payload as fallback.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from navigation.models import OutdoorNode

HTML_HEAD = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>CampusNav Outdoor QR Sheet</title>
<style>
body{font-family:Arial,sans-serif;background:#f1f5f9;margin:0;padding:24px}
h1{font-size:20px} p.sub{color:#64748b;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;text-align:center;page-break-inside:avoid}
.card img{width:180px;height:180px}
.card h2{font-size:15px;margin:8px 0 2px}
.card code{font-size:11px;color:#475569;word-break:break-all}
@media print{body{background:#fff}}
</style></head><body>
<h1>CampusNav — Outdoor QR Locations</h1>
<p class="sub">Scan any code with CampusNav Scan to set your current outdoor location.</p>
<div class="grid">
"""


class Command(BaseCommand):
    help = 'Writes a printable HTML sheet of outdoor QR codes.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='qr_codes/outdoor_qr_sheet.html')
        parser.add_argument('--only', nargs='*', default=[],
                            help='Limit to these outdoor node ids')
        parser.add_argument('--api-base', default='http://localhost:8000',
                            help='Base URL used for QR image links')

    def handle(self, *args, **options):
        qs = OutdoorNode.objects.filter(is_active=True).order_by('node_id')
        if options['only']:
            wanted = {v.upper() for v in options['only']}
            qs = qs.filter(node_id__in=[n.node_id for n in qs if n.node_id.upper() in wanted])
        nodes = list(qs)
        if not nodes:
            self.stdout.write(self.style.WARNING('No active outdoor nodes found.'))
            return
        cards = []
        for n in nodes:
            payload = n.qr_code or f'CAMPUSNAV|OUTDOOR|{n.node_id}'
            img = f"{options['api_base'].rstrip('/')}/api/qr/outdoor/{n.node_id}/"
            cards.append(
                f'<div class="card"><img src="{img}" alt="QR for {n.name}">'
                f'<h2>{n.name}</h2><code>{payload}</code></div>')
        out = Path(options['output'])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(HTML_HEAD + '\n'.join(cards) + '\n</div></body></html>', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(cards)} QR cards to {out}"))
