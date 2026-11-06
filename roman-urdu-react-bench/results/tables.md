# Results

## Accuracy (lenient scoring, Wilson 95% CI)

| Model | Method | Form | Correct | Accuracy | Strict | Op. error | Skipped lookup |
|---|---|---|---|---|---|---|---|
| llama3.1:8b | direct | English | 42/96 | 43.8% [34.3, 53.7] | 43.8% | 0.0% | 0.0% |
| llama3.1:8b | direct | Roman Urdu | 47/96 | 49.0% [39.2, 58.8] | 47.9% | 0.0% | 0.0% |
| llama3.1:8b | direct | Roman Urdu (chat spelling) | 35/96 | 36.5% [27.5, 46.4] | 36.5% | 0.0% | 0.0% |
| llama3.1:8b | react_en_shot | English | 84/96 | 87.5% [79.4, 92.7] | 87.5% | 0.0% | 0.0% |
| llama3.1:8b | react_en_shot | Roman Urdu | 63/96 | 65.6% [55.7, 74.4] | 64.6% | 1.0% | 6.2% |
| llama3.1:8b | react_en_shot | Roman Urdu (chat spelling) | 60/96 | 62.5% [52.5, 71.5] | 62.5% | 2.1% | 6.2% |
| llama3.1:8b | react_ru_shot | Roman Urdu | 73/95 | 76.8% [67.4, 84.2] | 75.8% | 4.2% | 1.1% |
| llama3.1:8b | react_ru_shot | Roman Urdu (chat spelling) | 83/96 | 86.5% [78.2, 91.9] | 85.4% | 0.0% | 0.0% |
| llama3.1:8b | translate_react | Roman Urdu | 73/96 | 76.0% [66.6, 83.5] | 74.0% | 0.0% | 0.0% |
| llama3.1:8b | translate_react | Roman Urdu (chat spelling) | 72/96 | 75.0% [65.5, 82.6] | 75.0% | 0.0% | 0.0% |
| llama3.2:3b | direct | English | 67/96 | 69.8% [60.0, 78.1] | 57.3% | 0.0% | 0.0% |
| llama3.2:3b | direct | Roman Urdu | 68/96 | 70.8% [61.1, 79.0] | 69.8% | 0.0% | 0.0% |
| llama3.2:3b | direct | Roman Urdu (chat spelling) | 51/96 | 53.1% [43.2, 62.8] | 51.0% | 0.0% | 0.0% |
| llama3.2:3b | react_en_shot | English | 75/96 | 78.1% [68.9, 85.2] | 78.1% | 0.0% | 0.0% |
| llama3.2:3b | react_en_shot | Roman Urdu | 45/96 | 46.9% [37.2, 56.8] | 46.9% | 12.5% | 1.0% |
| llama3.2:3b | react_en_shot | Roman Urdu (chat spelling) | 40/96 | 41.7% [32.3, 51.7] | 41.7% | 9.4% | 3.1% |
| llama3.2:3b | react_ru_shot | Roman Urdu | 61/96 | 63.5% [53.6, 72.5] | 62.5% | 6.2% | 2.1% |
| llama3.2:3b | react_ru_shot | Roman Urdu (chat spelling) | 43/96 | 44.8% [35.2, 54.7] | 41.7% | 11.5% | 0.0% |
| llama3.2:3b | translate_react | Roman Urdu | 65/96 | 67.7% [57.8, 76.2] | 67.7% | 0.0% | 3.1% |
| llama3.2:3b | translate_react | Roman Urdu (chat spelling) | 55/96 | 57.3% [47.3, 66.7] | 57.3% | 0.0% | 4.2% |
| qwen2.5:3b | direct | English | 54/96 | 56.2% [46.3, 65.7] | 56.2% | 0.0% | 0.0% |
| qwen2.5:3b | direct | Roman Urdu | 31/96 | 32.3% [23.8, 42.2] | 31.2% | 0.0% | 0.0% |
| qwen2.5:3b | direct | Roman Urdu (chat spelling) | 24/96 | 25.0% [17.4, 34.5] | 24.0% | 0.0% | 0.0% |
| qwen2.5:3b | react_en_shot | English | 88/96 | 91.7% [84.4, 95.7] | 91.7% | 0.0% | 4.2% |
| qwen2.5:3b | react_en_shot | Roman Urdu | 55/95 | 57.9% [47.8, 67.3] | 57.9% | 8.4% | 8.4% |
| qwen2.5:3b | react_en_shot | Roman Urdu (chat spelling) | 35/96 | 36.5% [27.5, 46.4] | 36.5% | 10.4% | 8.3% |
| qwen2.5:3b | react_ru_shot | Roman Urdu | 52/96 | 54.2% [44.2, 63.8] | 54.2% | 9.4% | 10.4% |
| qwen2.5:3b | react_ru_shot | Roman Urdu (chat spelling) | 43/96 | 44.8% [35.2, 54.7] | 44.8% | 15.6% | 10.4% |
| qwen2.5:3b | translate_react | Roman Urdu | 54/96 | 56.2% [46.3, 65.7] | 56.2% | 8.3% | 10.4% |
| qwen2.5:3b | translate_react | Roman Urdu (chat spelling) | 42/96 | 43.8% [34.3, 53.7] | 43.8% | 5.2% | 6.2% |
| qwen2.5:7b | direct | English | 85/96 | 88.5% [80.6, 93.5] | 88.5% | 0.0% | 0.0% |
| qwen2.5:7b | direct | Roman Urdu | 82/96 | 85.4% [77.0, 91.1] | 85.4% | 0.0% | 0.0% |
| qwen2.5:7b | direct | Roman Urdu (chat spelling) | 77/96 | 80.2% [71.1, 86.9] | 80.2% | 0.0% | 0.0% |
| qwen2.5:7b | react_en_shot | English | 84/96 | 87.5% [79.4, 92.7] | 85.4% | 0.0% | 0.0% |
| qwen2.5:7b | react_en_shot | Roman Urdu | 85/96 | 88.5% [80.6, 93.5] | 87.5% | 0.0% | 3.1% |
| qwen2.5:7b | react_en_shot | Roman Urdu (chat spelling) | 78/96 | 81.2% [72.3, 87.8] | 81.2% | 1.0% | 2.1% |
| qwen2.5:7b | react_ru_shot | Roman Urdu | 81/96 | 84.4% [75.8, 90.3] | 84.4% | 7.3% | 1.0% |
| qwen2.5:7b | react_ru_shot | Roman Urdu (chat spelling) | 73/96 | 76.0% [66.6, 83.5] | 76.0% | 10.4% | 1.0% |
| qwen2.5:7b | translate_react | Roman Urdu | 83/96 | 86.5% [78.2, 91.9] | 83.3% | 0.0% | 2.1% |
| qwen2.5:7b | translate_react | Roman Urdu (chat spelling) | 80/96 | 83.3% [74.6, 89.5] | 83.3% | 3.1% | 0.0% |

## Paired differences (percentage points, bootstrap 95% CI over items)

| Model | Comparison | Difference | 95% CI | Items |
|---|---|---|---|---|
| llama3.1:8b | react_en_shot: Roman Urdu minus English | -21.9 | [-32.3, -11.5] | 96 |
| llama3.1:8b | react_en_shot: chat spelling minus English | -25.0 | [-35.4, -13.5] | 96 |
| llama3.1:8b | react_en_shot: chat spelling minus Roman Urdu | -3.1 | [-14.6, +8.3] | 96 |
| llama3.1:8b | direct: Roman Urdu minus English | +5.2 | [-7.3, +16.7] | 96 |
| llama3.1:8b | English: ReAct minus direct | +43.8 | [+32.3, +55.2] | 96 |
| llama3.1:8b | Roman Urdu: ReAct minus direct | +16.7 | [+2.1, +31.2] | 96 |
| llama3.1:8b | Roman Urdu: Roman Urdu example minus English example | +11.6 | [+0.0, +24.2] | 95 |
| llama3.1:8b | Roman Urdu: translate-then-ReAct minus ReAct | +10.4 | [-2.1, +22.9] | 96 |
| llama3.1:8b | Chat spelling: translate-then-ReAct minus ReAct | +12.5 | [-1.0, +26.0] | 96 |
| llama3.1:8b | name set B minus A (English) | +4.2 | [-6.2, +14.6] | 48 |
| llama3.1:8b | name set B minus A (Roman Urdu) | -18.8 | [-37.5, +2.1] | 48 |
| llama3.1:8b | name set B minus A (Roman Urdu (chat spelling)) | -8.3 | [-22.9, +6.2] | 48 |
| llama3.2:3b | react_en_shot: Roman Urdu minus English | -31.2 | [-41.7, -19.8] | 96 |
| llama3.2:3b | react_en_shot: chat spelling minus English | -36.5 | [-46.9, -26.0] | 96 |
| llama3.2:3b | react_en_shot: chat spelling minus Roman Urdu | -5.2 | [-13.5, +3.1] | 96 |
| llama3.2:3b | direct: Roman Urdu minus English | +1.0 | [-9.4, +11.5] | 96 |
| llama3.2:3b | English: ReAct minus direct | +8.3 | [-4.2, +21.9] | 96 |
| llama3.2:3b | Roman Urdu: ReAct minus direct | -24.0 | [-37.5, -10.4] | 96 |
| llama3.2:3b | Roman Urdu: Roman Urdu example minus English example | +16.7 | [+5.2, +29.2] | 96 |
| llama3.2:3b | Roman Urdu: translate-then-ReAct minus ReAct | +20.8 | [+9.4, +31.2] | 96 |
| llama3.2:3b | Chat spelling: translate-then-ReAct minus ReAct | +15.6 | [+4.2, +27.1] | 96 |
| llama3.2:3b | name set B minus A (English) | +2.1 | [-6.2, +10.4] | 48 |
| llama3.2:3b | name set B minus A (Roman Urdu) | -2.1 | [-16.7, +10.4] | 48 |
| llama3.2:3b | name set B minus A (Roman Urdu (chat spelling)) | -8.3 | [-22.9, +6.2] | 48 |
| qwen2.5:3b | react_en_shot: Roman Urdu minus English | -34.7 | [-44.2, -25.3] | 95 |
| qwen2.5:3b | react_en_shot: chat spelling minus English | -55.2 | [-65.6, -44.8] | 96 |
| qwen2.5:3b | react_en_shot: chat spelling minus Roman Urdu | -22.1 | [-31.6, -13.7] | 95 |
| qwen2.5:3b | direct: Roman Urdu minus English | -24.0 | [-35.4, -13.5] | 96 |
| qwen2.5:3b | English: ReAct minus direct | +35.4 | [+24.0, +45.8] | 96 |
| qwen2.5:3b | Roman Urdu: ReAct minus direct | +26.3 | [+14.7, +38.9] | 95 |
| qwen2.5:3b | Roman Urdu: Roman Urdu example minus English example | -3.2 | [-13.7, +6.3] | 95 |
| qwen2.5:3b | Roman Urdu: translate-then-ReAct minus ReAct | -1.1 | [-10.5, +8.4] | 95 |
| qwen2.5:3b | Chat spelling: translate-then-ReAct minus ReAct | +7.3 | [-5.2, +18.8] | 96 |
| qwen2.5:3b | name set B minus A (English) | +4.2 | [-4.2, +12.5] | 48 |
| qwen2.5:3b | name set B minus A (Roman Urdu) | -2.1 | [-12.8, +8.5] | 47 |
| qwen2.5:3b | name set B minus A (Roman Urdu (chat spelling)) | -2.1 | [-12.5, +6.2] | 48 |
| qwen2.5:7b | react_en_shot: Roman Urdu minus English | +1.0 | [-6.2, +7.3] | 96 |
| qwen2.5:7b | react_en_shot: chat spelling minus English | -6.2 | [-14.6, +2.1] | 96 |
| qwen2.5:7b | react_en_shot: chat spelling minus Roman Urdu | -7.3 | [-15.6, +1.0] | 96 |
| qwen2.5:7b | direct: Roman Urdu minus English | -3.1 | [-8.3, +2.1] | 96 |
| qwen2.5:7b | English: ReAct minus direct | -1.0 | [-9.4, +7.3] | 96 |
| qwen2.5:7b | Roman Urdu: ReAct minus direct | +3.1 | [-4.2, +10.4] | 96 |
| qwen2.5:7b | Roman Urdu: Roman Urdu example minus English example | -4.2 | [-13.5, +4.2] | 96 |
| qwen2.5:7b | Roman Urdu: translate-then-ReAct minus ReAct | -2.1 | [-8.3, +4.2] | 96 |
| qwen2.5:7b | Chat spelling: translate-then-ReAct minus ReAct | +2.1 | [-6.2, +10.4] | 96 |
| qwen2.5:7b | name set B minus A (English) | +0.0 | [-8.3, +8.3] | 48 |
| qwen2.5:7b | name set B minus A (Roman Urdu) | -2.1 | [-12.5, +8.3] | 48 |
| qwen2.5:7b | name set B minus A (Roman Urdu (chat spelling)) | +0.0 | [-10.4, +10.4] | 48 |
