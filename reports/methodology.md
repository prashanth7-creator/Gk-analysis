# Methodology
## Euro 2024 Goalkeeper Individual Performance Analysis

---

### 1. Data Source

All data was sourced from **StatsBomb Open Data** (Euro 2024, `competition_id = 55`, `season_id = 282`), accessed via the `statsbombpy` Python library. StatsBomb provides event-level data for every action in each match, including shot details (location, xG, outcome), goalkeeper-specific events, and pass sequences.

---

### 2. Data Collection and Processing

All 51 Euro 2024 matches were loaded and their event streams concatenated into a single dataset. Three sub-tables were extracted:

**Shots Faced** — All shot events were filtered and enriched with the opposing goalkeeper's name. For each shot, the following attributes were retained: StatsBomb xG, outcome (Saved, Goal, Blocked, Off Target, etc.), shot location (x, y), body part, and technique.

**Goalkeeper Events** — Events of type `Goal Keeper` were extracted and the `goalkeeper.type` sub-field was decoded to classify each action as: Shot Faced, Shot Saved, Collected (aerial claim), Punch, Keeper Sweeper, or Goal Conceded.

**Goal Kicks** — Pass events with `pass_type = Goal Kick` were extracted, retaining pass length and end location to measure distribution range and direction.

Goalkeepers who appeared in fewer than **2 matches** were excluded to remove one-off substitutes from the analysis.

---

### 3. Performance Metrics

The following per-goalkeeper metrics were computed:

| Metric | Description |
|---|---|
| Shots Faced | Total shots on record facing that goalkeeper |
| xG Faced | Cumulative expected goals from all shots faced |
| Saves | Shots resulting in a save |
| Goals Conceded | Shots resulting in a goal |
| Save % | Saves ÷ Shots on Target × 100 |
| Goals Prevented (GSaE) | xG Faced − Goals Conceded |
| Sweeper / Match | Keeper Sweeper actions per match |
| Claims / Match | Aerial claims (Collected) per match |
| Punches / Match | Punches per match |
| Goal Kicks / Match | Goal kicks per match |
| Avg. Kick Length | Mean distance of goal kicks (metres) |

---

### 4. Z-Score Normalisation

To compare goalkeepers across metrics with different scales, each metric was standardised into a Z-score:

**Z = (x − μ) ÷ σ**

where μ and σ are the tournament mean and standard deviation across all qualifying goalkeepers. For metrics where a lower value is better (goals conceded, xG faced), the Z-score was negated so that a positive value always indicates better-than-average performance.

Seven metrics were Z-scored: Save %, Goals Prevented, Sweeper/Match, Claims/Match, Goals Conceded, xG Faced, and Goals Prevented/Match.

---

### 5. Composite Ranking

A single composite performance score was constructed as a weighted sum of five Z-scores, with weights reflecting the relative importance of each dimension to overall goalkeeping quality:

| Metric | Weight |
|---|---|
| Goals Prevented (GSaE) | 35% |
| Save % | 30% |
| Sweeper Actions / Match | 15% |
| Claims / Match | 10% |
| Goals Conceded (inverted) | 10% |

**Composite Score = 0.35 × z(GP) + 0.30 × z(Sv%) + 0.15 × z(Sweeper) + 0.10 × z(Claims) + 0.10 × z(GA)**

Goals Prevented was weighted most heavily because it directly captures outperformance relative to expected goals, accounting for shot quality rather than volume. Save percentage was weighted second as a widely understood measure of shot-stopping reliability.

---

### 6. Visualisation

**Tournament-level charts** — Save percentage bar chart for all qualifying goalkeepers; xG faced vs goals conceded scatter plot (bubble size = matches played, colour = goals prevented); stacked bar chart of sweeper, claim, and punch actions per match; composite ranking bar chart; goal kick distribution (kicks per match and average kick length vs goals prevented per match); top-5 and top-10 radar charts comparing normalised metrics across the leading goalkeepers.

**Individual dashboards** — A 2×3 panel layout per goalkeeper containing: a shot map showing saves (teal) and goals conceded (red star) plotted at shot origin; punch locations on pitch; long distribution arrows (≥32 m, orange); short distribution arrows (<32 m, blue); and a Z-score radar profile across seven performance dimensions. Dashboards were generated for the top 3 ranked goalkeepers.

**Deep-dive individual analysis** — Per-goalkeeper reports including: a dark-theme shot map with bubble size scaled to xG; a detailed green-pitch shot map with xG annotations for high-danger chances (xG > 0.30); a GSaE vs Save % quadrant scatter with tournament regression line and quadrant classification (Elite / Quality over Quantity / Underperforming); a GSaE horizontal ranking bar chart highlighting the selected goalkeeper; and a full-pitch action heatmap showing the spatial distribution of saves, claims, sweeper actions, punches, and goals conceded plotted in StatsBomb coordinates (x: 0–120, y: 0–80).
