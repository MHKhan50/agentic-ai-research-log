# Notes (full run, 5-6 Nov 2026)

1. qwen2.5:7b kept its ReAct accuracy in Roman Urdu (87.5% English, 88.5% Roman Urdu), while qwen2.5:3b fell from 91.7% to 57.9%. With only two sizes I cannot say why; one guess is that the larger model handles Roman Urdu words more reliably. The 7B model was also strong with the database in the prompt (88.5% vs 85.4%).

2. For the two Llama models, answering directly showed no Roman Urdu gap, but ReAct did (llama3.1:8b -21.9 points, llama3.2:3b -31.2). qwen2.5:3b lost accuracy in both. In the ReAct runs, Roman Urdu brought more wrong arithmetic operators (llama3.2:3b 0% to 12.5%) and more skipped lookups (qwen2.5:3b 4.2% to 8.4%), so the loop gives more chances for a misread word to turn into a wrong step.

3. In a pilot, sending the whole ReAct transcript as one user message made llama3.2:3b repeat its first step until the step limit (7% in English). Sending each step as a separate chat turn, with the same grading, gave 78.1%. How an agent loop is presented to a chat model can change results as much as the language does, so benchmarks should report and test this.
