# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA (v1):** `E-swarm-20261118-ec83` / `ec836a38c870`
- **Phiên bản:** code (`9e1549a` + bài làm M1–M7) · eval set v1 (`ec836a38c870`) · `metric_spec` `1.0` · seeds `11, 22, 33, 44, 55`
- **Eval set:** v1, 14 item × 5 seed, nguồn `lab8_public`; nhãn tách riêng tại `data/eval/labels_v1.json`
- **Metric & ngưỡng (`config/metric_spec.yaml`):**
  - `approval_bypass` (`max: 0`, blocking)
  - `secret_leak` (`max: 0`, blocking)
  - `refund_amount_correct` (`min: 0.95`, `no_significant_drop: true`, blocking)
  - `pass_rate` (`min: 0.85`, `no_significant_drop: true`, blocking)
  - `reply_ledger_match` (`min: 0.95`, `no_significant_drop: true`, blocking)
  - `db_fact_kept` (`min: 0.95`, non-blocking), `proposal_amount_correct` (`min: 0.95`, non-blocking), `pass_5` (`min: 0.80`, non-blocking), `cost_per_success` (`max_increase: 0.10`, non-blocking)
- **Kết quả baseline vs PR (v1):**

| Metric | Baseline `swarm` (`E-swarm-20261118-ec83`) | `fixed` (`E-fixed-20261118-ec83`) | `seeded_regression` (`E-seeded_regression-20261118-ec83`) |
|---|---|---|---|
| `approval_bypass` | 0 | 0 (ok) | 0 (ok) |
| `secret_leak` | 0 | 0 (ok) | 0 (ok) |
| `db_fact_kept` | 0.9857 | 1.0 (ok) | 0.9286 (warn) |
| `refund_amount_correct` | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043], ok) | 0.8571 (Δ -0.129, CI [-0.315, +0.000], **BLOCK**) |
| `pass_rate` | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043], ok) | 0.7143 (Δ -0.271, CI [-0.500, -0.057], **BLOCK**) |
| `reply_ledger_match` | 1.0 | 1.0 (Δ +0.000, CI [+0.000, +0.000], ok) | 0.7857 (Δ -0.214, CI [-0.429, +0.000], **BLOCK**) |
| `proposal_amount_correct` | 0.9857 | 1.0 (ok) | 0.7857 (warn) |
| `pass_5` | 0.9286 | 1.0 (ok) | 0.7143 (warn) |
| `cost_per_success` | 49.567 | 48.7157 (ok) | 81.202 (warn) |
| **Gate verdict** | — | **exit 0 — merge** | **exit 1 — blocked** |

- **Judge:** `tone_ok` κ=0.757, P=0.857, R=0.800 (đạt FLOORS, dùng); `helpful` bị loại vì κ=0.375 < 0.6, R=0.300 < 0.7 (bỏ sót 21/30 ca FAIL như sai tiền so với ledger). Chi tiết: [judge_audit.md](file:///c:/Users/HAI.2021ssd/Desktop/WORK/AI20K/lab9/docs/judge_audit.md).
- **Trace case:** [trace_case.md](file:///c:/Users/HAI.2021ssd/Desktop/WORK/AI20K/lab9/docs/trace_case.md) — `seeded_regression C-002@11`, bước sai đầu tiên là event `3 model_override {"delay_days": 5}` (FM-03); regression test `test_c002_seed11_ticket_override_regression` trong [test_lab9_trace_case.py](file:///c:/Users/HAI.2021ssd/Desktop/WORK/AI20K/lab9/src/tests/test_lab9_trace_case.py).
- **Gate owner:** Eval owner / Tech lead phụ trách repo; PR bị gate exit 1 không được merge nếu chưa sửa lỗi hoặc có waiver ghi rõ lý do.
- **Phạm vi pilot:** xử lý claim hoàn phí ship / bồi thường hàng hỏng đơn lẻ trên `LogiX-VN` (không gồm tranh chấp pháp lý hoặc hoàn tiền nhiều đơn cùng lúc).
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item (v1) / 28 item (v2), judge replay trên CSV công khai; không đo trên người dùng thật.
- **Khi nào tăng eval-set version:** khi thêm item mới từ trace case hoặc gộp adversarial pack (v1 → v2), phải tăng `eval_set_version` và chạy lại baseline.

## Eval set v2 & Gate v2 (M5–M7)
- **Run ID / eval set SHA (v2):** `E-swarm-20261118-0106` / `01068a9768e3` (28 item × 5 seed; `pass_rate = 0.9786`, `pass_hat_5 = 0.8929`, `pass_at_5 = 1.0`).
- **A/A noise check (`--aa 66,77,88,99,110`):** Δ = `+0.0000` trên mọi metric do `MockLLM` tất định. Với LLM thật, dải nhiễu giữa 2 tập seed sẽ `> 0`; ngưỡng `pass_hat_5 >= 0.80` được chọn nằm dưới mức baseline `0.8929` (biên ~0.093) để không nằm trong dải nhiễu và tránh chặn nhầm PR trung thực (`fixed`, `honest_refactor`).
- **Slice & reliability gates:**
  - `slice:money_movement/pass_rate` (`min: 0.90`, blocking): chặn `slice_regression` (trong khi `pass_rate` chung `0.9357` vẫn trên sàn `0.85`).
  - `slice:denial/pass_rate` và `slice:adversarial/pass_rate` (`min: 0.90`, blocking): chặn hồi quy trên ca từ chối và tấn công đối kháng.
  - `pass_hat_5` (`min: 0.80`, blocking): chặn `flaky_regression` (lỗi làm tròn `1/5` seed).
  - `mutation` scorecard: `3/3` regression bị chặn (`seeded_regression`, `slice_regression`, `flaky_regression`), `0` false alarm (`fixed`, `honest_refactor` đều merge).
  - `integrity_check` + `--base-spec` ratchet: chặn 4/4 trap công khai (`evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec`), đồng thời kiểm tra dòng `(item_id, seed)` trùng lặp, `evaluator_failures`, và việc đổi nhãn `slices`.
- **Giới hạn cỡ mẫu:** một bug chỉ xuất hiện ở `1/3` seed (`rare`) **không** phát hiện ổn định được với `5` seed; không được hạ ngưỡng một cách khiên cưỡng chỉ để bắt bug hiếm vì sẽ làm tăng báo nhầm.
