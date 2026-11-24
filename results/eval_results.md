# Retrieval evaluation (k=5, 40 queries, 179 products)

## all (40 queries)

| method | Hit@5 | MRR | nDCG@5 | P@5 |
|---|---|---|---|---|
| keyword | 0.78 | 0.70 | 0.50 | 0.44 |
| bm25 | 0.75 | 0.62 | 0.46 | 0.42 |
| semantic | 0.95 | 0.87 | 0.65 | 0.57 |
| hybrid | 0.97 | 0.86 | 0.63 | 0.56 |

## keyword-style (10 queries)

| method | Hit@5 | MRR | nDCG@5 | P@5 |
|---|---|---|---|---|
| keyword | 1.00 | 1.00 | 0.73 | 0.62 |
| bm25 | 1.00 | 1.00 | 0.73 | 0.62 |
| semantic | 1.00 | 1.00 | 0.73 | 0.62 |
| hybrid | 1.00 | 1.00 | 0.73 | 0.62 |

## natural-language (30 queries)

| method | Hit@5 | MRR | nDCG@5 | P@5 |
|---|---|---|---|---|
| keyword | 0.70 | 0.60 | 0.43 | 0.38 |
| bm25 | 0.67 | 0.49 | 0.37 | 0.35 |
| semantic | 0.93 | 0.83 | 0.63 | 0.56 |
| hybrid | 0.97 | 0.81 | 0.60 | 0.54 |

## Average latency per query (ms, this machine)

| method | ms |
|---|---|
| keyword | 3.3 |
| bm25 | 0.2 |
| semantic | 39.1 |
| hybrid | 39.7 |

## Examples where keyword lookup missed but semantic search found it

- "something to keep my coffee hot on the drive to work" -> Urbanest Vacuum Insulated Tumbler
- "music at the pool party, it might get splashed" -> Kairo Portable Bluetooth Speaker Lite
- "sore muscles after the gym" -> Peakform High Density Foam Roller Max
- "protect my credit cards from being scanned by thieves" -> Urban Trail RFID Blocking Leather Wallet Plus
- "my plants die when I go on vacation" -> Casa Nova Self-Watering Planter Max
- "record my mountain biking rides" -> Kairo 4K Action Camera
- "learn coding from scratch" -> Pageturn Press Python Crash Course Book Max
- "gift for a 7 year old who likes making things" -> Brickly Building Blocks Set Lite

## Queries semantic search still misses (top 5)

- "read novels outside in bright sun without eye strain" wanted ['ebook_reader'], got ['Urban Trail Polarized Sunglasses 2.0', 'Urban Trail Polarized Sunglasses Neo', 'Urbanest Blackout Curtains']
- "see where I am walking at night on a hike, hands free" wanted ['headlamp'], got ['Trailblaze Waterproof Trekking Shoes Plus', 'Trailblaze Waterproof Trekking Shoes Neo', 'Fitora Waterproof Trekking Shoes']
