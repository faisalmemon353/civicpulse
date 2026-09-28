# Required Submission Evidence (§4 & §5.7)

This directory contains the visual evidence required by the assignment rubric.

## Checklist of Required Screenshots

1. **`protection.png` (§4.A — 3 marks):**
   - Screenshot of GitHub repository settings under **Branches** $\rightarrow$ **Branch protection rules** for `main`.
   - Must visibly show:
     - "Require a pull request before merging" (with $\ge 1$ approval required).
     - "Require status checks to pass before merging" (with CI checks selected).
     - "Do not allow bypassing the above settings".

2. **`conflict.png` (§4.A — 3 marks):**
   - Screenshot of the deliberate merge conflict on real code.
   - Must show the conflict markers (`<<<<<<< HEAD`, `=======`, `>>>>>>>`), the GitHub PR or git CLI conflict resolution, and the merge commit.
   - Accompanying 2–4 sentences explaining why the winning version was chosen (also documented in PR #24).

3. **`blocked_merge.png` & `green_pipeline.png` (§4.I — 1 mark):**
   - Screenshot 1: A Pull Request with a deliberately failing test showing the red `X` CI check and the disabled/blocked merge button.
   - Screenshot 2: The fix pushed in the same PR showing the check turn green and the merge button becoming enabled.

4. **`hpa_scale_out.png` & `scaling_chart.png` (§4.H — 4 marks):**
   - Screenshot 1: Terminal output of `kubectl get hpa backend-hpa -n civicpulse -w` while running `k6 run load/k6-script.js`, capturing replicas scaling out from 2 up to 4+ as CPU exceeds 60%.
   - Screenshot 2: A simple plot/chart of replicas over time against the offered virtual user (VU) load.

5. **`network_isolation.png` (§4.G — 4 marks):**
   - Terminal screenshot demonstrating:
     ```bash
     docker compose exec frontend ping -c 1 database
     ```
     exiting with `ping: bad address 'database'`, proving physical network segmentation.
