Return strict JSON object with tasks (array length 3..5).
Each task requires:
- id
- type (scenario|artifact_upload)
- title
- prompt
- topic
- rubric (array 3..6)
- required (bool)

Mix scenario and artifact_upload tasks when suitable.
Calibrate difficulty with difficulty_profile and KSA context.
