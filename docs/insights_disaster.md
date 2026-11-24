# 分析結果：防災 / Insights: disaster preparedness

> 出典：国土地理院「指定緊急避難場所・指定避難所データ」。最新の状況は必ず仙台市に確認してください。記述統計のみ。
> Source: GSI evacuation-site data. Always check the City of Sendai for the current situation. Descriptive only.

## 日本語

1. **仙台市には指定避難所231か所（うち福祉避難所36か所）と、指定緊急避難場所314か所が登録されている。** 196か所は避難所と避難場所を兼ねる（住所が同一）。
2. **津波に対応した避難場所は82か所で、宮城野区51か所・若林区26か所（仙台東部道路の避難階段5か所を含む）・太白区5か所。** 沿岸部の東側に集中している。
3. **津波避難場所82か所のうち62か所は、2階以上・屋上・共用廊下などへの避難（垂直避難）が前提。** 学校24、集合住宅18、津波避難タワー7、避難の丘6、津波避難ビル5、東部道路の避難階段5。
4. **人口1万人あたりの指定避難所（福祉を除く）は泉区2.30が最多、若林区1.40が最少。** ただし収容人数はデータにないため、数の比較にとどまる。
5. **災害の種類による偏り：** 地震257か所、洪水・土砂災害・内水氾濫は各189か所に対し、大規模な火事は8か所のみ、高潮・火山現象は0か所。
6. **データ品質：** CSVとGeoJSONのIDが完全一致、重複なし、全地点が仙台市内。避難所と住所同一とされた196か所はすべて避難所一覧に存在。住所に区名がない5か所（東部道路の避難階段）は、区の境界データ（国土数値情報 N03）で若林区と判定。住所に区名がある540か所もすべて境界と一致。

## English

1. **Sendai has 231 designated shelters (36 of them welfare shelters) and 314 emergency evacuation sites registered.** 196 addresses are both.
2. **82 sites are designated for tsunami:** 51 in Miyagino, 26 in Wakabayashi (including 5 staircases on the Sendai Tōbu expressway), 5 in Taihaku. They're concentrated on the eastern coast.
3. **62 of the 82 tsunami sites mean going up: to the 2nd floor or higher, a roof or an outside corridor (vertical evacuation).** By type: 24 schools, 18 housing blocks, 7 tsunami towers, 6 evacuation hills, 5 evacuation buildings, 5 expressway staircases.
4. **Shelters per 10,000 residents (welfare excluded): Izumi has the most (2.30), Wakabayashi the fewest (1.40).** Capacity isn't in the data, so this compares counts only.
5. **Uneven by disaster type:** 257 sites for earthquakes and 189 each for floods, landslides and inland flooding, but only 8 for large fires and none for storm surge or volcanoes.
6. **Data quality:** the CSV and GeoJSON versions hold identical IDs; no duplicates; every site is inside Sendai; all 196 sites flagged as sharing a shelter's address are in the shelter list. The 5 sites with no ward in their address (the expressway staircases) are placed in Wakabayashi using the ward boundaries (国土数値情報 N03); the other 540 sites' address wards all match the boundaries.
