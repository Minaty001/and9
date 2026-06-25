# Bug Hunter Report

- Findings reviewed: 7
- Confirmed: 6
- Dismissed: 1
- Manual review: 0

## Confirmed Bugs
- BUG-1 | Medium | brain/reflex.py | Termux action_map commands always report success=true regardless of actual subprocess exit code. If a command fails (e.g., flashlight not available, ADB not connected, permission denied), the system lies to the user and the learning system records a false success.
  Confidence: 95 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: reflex.py:485-495 in _execute_termux runs subprocess.run() for action_map commands (flashlight, navigation, volume) but unconditionally returns {'success': True} regardless of result.returncode or result.stderr. The `am start` path at line 471 correctly checks returncode, proving the omission is unintentional. On Termux without Termux:API, `termux-torch on/off` returns non-zero exit but is reported as success. The try/except at line 499 only catches exceptions (e.g., FileNotFoundError), not non-zero exit codes.
- BUG-2 | Medium | brain/reflex.py | Navigation and volume actions (go_home, go_back, volume_up, volume_down) have Termux action_map entries but lack requires_termux=True. On Android they fall through to _execute_fallback which only logs a desktop simulation message instead of running the actual Termux commands.
  Confidence: 98 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: reflex.py:241-284 registers volume_up, volume_down, go_home, go_back without requires_termux=True (defaults to False). reflex.py:439-442 dispatches based on `self._is_android and action.requires_termux` — since requires_termux is False, _execute_fallback runs instead of _execute_termux. The action_map dict at lines 476-483 defines Termux commands for all 4 actions, proving the developer intended Termux execution. The discrepancy between action_map (wired for Termux) and the missing flag is a clear oversight. On Android, users get desktop simulation messages instead of actual keyevent/torch commands.
- BUG-3 | Low | brain/reflex.py | Close app action (close_app) has requires_termux=True but no android_action package and no action_map entry. When executed on Android, it falls through to the catch-all 'return success: Action close_app noted (Termux)' without actually closing any app. The action is a silent no-op.
  Confidence: 95 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: close_app has requires_termux=True but no android_action (package) and no action_map entry. In _execute_termux: pkg=None→skip, 'close_app' not in action_map→skip, falls to line 497 catch-all returning success with no-op message. No actual command is executed. Downgraded to Low because closing arbitrary third-party apps on Android without root is technically infeasible via standard APIs (no 'force-stop' equivalent). The real behavioral issue is false success reporting, not the missing close implementation.
- BUG-4 | Low | brain/decision.py | TIMER intent is referenced in decision.py _extract_entities but is not defined in config.py INTENTS list (LINE-37). The check for number/quantity extraction on TIMER intent is dead code that never executes.
  Confidence: 100 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: decision.py:370 references 'TIMER' in the _extract_entities number extraction block. config.py:53-74 INTENTS list does not include TIMER. The condition `intent == 'TIMER'` can never be True because no brain component ever produces TIMER as an intent. This is dead/inconsistent code. Low severity — no runtime crash, but a cross-file inconsistency that could cause confusion during maintenance.
- BUG-5 | Low | training/evaluate.py | Evaluation test set split uses random.shuffle() without a fixed seed, making evaluation results non-deterministic. Each run produces different test sets and therefore different accuracy metrics, undermining the ability to compare model improvements over time.
  Confidence: 90 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: evaluate.py:45 calls random.shuffle(examples) without a prior random.seed() call. Each evaluation selects a different 15% test subset, producing non-deterministic accuracy metrics. The same model evaluated twice on the same dataset yields different results. This undermines regression testing and model comparison. Low severity because the evaluate script is for ad-hoc assessment, but the data integrity impact is real.
- BUG-6 | Low | training/train.py | Training data split uses random.shuffle() without a fixed seed, making training non-reproducible. Each training run produces different train/val/test splits, so the same training script on the same data yields different models and different metrics.
  Confidence: 90 (high) | INDEPENDENTLY_VERIFIED
  Analysis: Independent code read confirms: train.py:54 calls random.shuffle(examples) without a prior random.seed() call. Each training run produces different train/val/test splits, making training non-reproducible. The same training command on the same data yields different model weights and metrics. Note: even with a seed for split_data, full reproducibility also requires seeding np.random (used in weight init at neural.py:211) and controlling mini-batch order. This bug specifically addresses the data split component.

## Manual Review
- None

## Dismissed Findings
- BUG-7 | brain/reflex.py | Dead logic in _execute_termux: both branches of if/else on cmd.startswith('input') execute exactly the same code (cmd.split()). The conditional is redundant.
  Analysis: Independent code read confirms: both branches of the if/else at reflex.py:487-494 execute identical code (cmd.split()). However, this pattern does NOT produce incorrect behavior — both 'input keyevent N' and 'termux-torch on/off' are correctly split and executed by subprocess.run(). The redundant conditional is dead code / style issue. Hunter SKILL.md explicitly excludes 'unused code' from scope. Skeptic's DISPROVE on this ground is correct. NOT A BEHAVIORAL BUG.
