import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type {
  KSAAbilities,
  KSAKnowledge,
  KSAProfile,
  KSASkills,
  KSAValue,
  KsaAssessmentAttempt,
  KsaAssessmentDefinition,
  KsaDrillAttempt,
  KsaDrillQuestion,
  KsaDrillTopic,
} from "../../types/chat";
import { Dialog } from "../common/Dialog";

type KsaPanelProps = {
  profile: KSAProfile | null;
  definition: KsaAssessmentDefinition | null;
  attempt: KsaAssessmentAttempt | null;
  drillTopics: KsaDrillTopic[];
  drillAttempt: KsaDrillAttempt | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  onReload: () => Promise<unknown> | void;
  onLoadDefinition: () => Promise<unknown>;
  onLoadLatestAttempt: () => Promise<unknown>;
  onStartAssessment: () => Promise<unknown>;
  onSaveAnswers: (attemptId: string, answers: Record<string, unknown>) => Promise<unknown>;
  onCompleteAssessment: (attemptId: string) => Promise<unknown>;
  onLoadDrillTopics: () => Promise<unknown>;
  onLoadLatestDrillAttempt: () => Promise<unknown>;
  onStartDrillAttempt: (topicKeys: string[]) => Promise<unknown>;
  onSaveDrillAnswers: (attemptId: string, answers: Record<string, unknown>) => Promise<unknown>;
  onCompleteDrillAttempt: (attemptId: string) => Promise<unknown>;
};

type RadarAxis = {
  key: string;
  label: string;
};

type AssessmentSection = "intro" | "phase1" | "knowledge" | "skills" | "abilities" | "complete";

const DREYFUS_LEVELS = ["Novice", "Advanced", "Competent", "Proficient", "Expert"];
const PHASE1_PAGE_SIZE = 3;

const KNOWLEDGE_AXES: RadarAxis[] = [
  { key: "stem_fundamentals", label: "STEM Fundamentals" },
  { key: "information_technology", label: "Information Technology" },
  { key: "humanities_social_sciences", label: "Humanities & Social Sciences" },
  { key: "languages_linguistics", label: "Languages & Linguistics" },
  { key: "business_commerce", label: "Business & Commerce" },
  { key: "legal_ethics", label: "Legal & Ethics" },
  { key: "health_wellness", label: "Health & Wellness" },
];

const SKILLS_AXES: RadarAxis[] = [
  { key: "literacy_numeracy", label: "Literacy & Numeracy" },
  { key: "digital_craft", label: "Digital Craft" },
  { key: "strategic_execution", label: "Strategic Execution" },
  { key: "operational_skills", label: "Operational Skills" },
  { key: "relational_skills", label: "Relational Skills" },
  { key: "research_inquiry", label: "Research & Inquiry" },
];

const ABILITIES_AXES: RadarAxis[] = [
  { key: "quantitative_reasoning", label: "Quantitative Reasoning" },
  { key: "verbal_comprehension", label: "Verbal Comprehension" },
  { key: "spatial_visualization", label: "Spatial Visualization" },
  { key: "executive_function", label: "Executive Function" },
  { key: "sensory_perceptual", label: "Sensory-Perceptual" },
  { key: "social_emotional_capacity", label: "Social-Emotional Capacity" },
  { key: "divergent_thinking", label: "Divergent Thinking" },
];

const KNOWLEDGE_GROUPS: Array<{ sliderKey: string; topics: string[] }> = [
  { sliderKey: "stem_it", topics: ["stem_fundamentals", "information_technology"] },
  { sliderKey: "humanities", topics: ["humanities_social_sciences", "languages_linguistics"] },
  { sliderKey: "business_legal", topics: ["business_commerce", "legal_ethics"] },
  { sliderKey: "health", topics: ["health_wellness"] },
];

const SKILL_GROUPS: Array<{ sliderKey: string; topics: string[] }> = [
  { sliderKey: "digital_ops", topics: ["digital_craft", "operational_skills"] },
  { sliderKey: "people_strat", topics: ["strategic_execution", "relational_skills"] },
  { sliderKey: "research", topics: ["research_inquiry", "literacy_numeracy"] },
];

function labelAnchorForAngle(angle: number): "start" | "middle" | "end" {
  const normalized = ((angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  if (normalized < 0.45 || normalized > Math.PI * 2 - 0.45 || (normalized > Math.PI - 0.45 && normalized < Math.PI + 0.45)) {
    return "middle";
  }
  return normalized < Math.PI ? "start" : "end";
}

function createPolygonPoints(points: Array<{ x: number; y: number }>) {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function toRecord(values: KSAKnowledge | KSASkills | KSAAbilities): Record<string, KSAValue> {
  return values as unknown as Record<string, KSAValue>;
}

function RadarPanel({
  title,
  subtitle,
  axes,
  values,
}: {
  title: string;
  subtitle: string;
  axes: RadarAxis[];
  values: Record<string, KSAValue>;
}) {
  const size = 340;
  const center = size / 2;
  const radius = 98;
  const angleStep = (Math.PI * 2) / axes.length;

  const rings = useMemo(() => {
    return [1, 2, 3, 4, 5].map((level) => {
      const ringRadius = (radius * level) / 5;
      const ringPoints = axes.map((_, index) => {
        const angle = -Math.PI / 2 + index * angleStep;
        return {
          x: center + ringRadius * Math.cos(angle),
          y: center + ringRadius * Math.sin(angle),
        };
      });
      return createPolygonPoints(ringPoints);
    });
  }, [angleStep, axes, center, radius]);

  const valuePoints = axes.map((axis, index) => {
    const angle = -Math.PI / 2 + index * angleStep;
    const value = Number(values[axis.key] ?? 1);
    const scaledRadius = (radius * Math.max(1, Math.min(5, value))) / 5;
    return {
      x: center + scaledRadius * Math.cos(angle),
      y: center + scaledRadius * Math.sin(angle),
    };
  });

  const valuePolygon = createPolygonPoints(valuePoints);

  return (
    <article className="ksa-panel-card">
      <header className="ksa-panel-head">
        <h5>{title}</h5>
        <p>{subtitle}</p>
      </header>
      <div className="ksa-radar-shell">
        <svg viewBox={`0 0 ${size} ${size}`} className="ksa-radar" role="img" aria-label={`${title} radar chart`}>
          <g>
            {rings.map((ring, index) => (
              <polygon key={`${title}-ring-${index}`} points={ring} className="ksa-ring" />
            ))}
            {valuePoints.map((point, index) => (
              <line key={`${title}-axis-${axes[index]?.key ?? index}`} x1={center} y1={center} x2={point.x} y2={point.y} className="ksa-axis-line" />
            ))}
            <polygon points={valuePolygon} className="ksa-value-shape" />
            {valuePoints.map((point, index) => (
              <circle key={`${title}-dot-${axes[index]?.key ?? index}`} cx={point.x} cy={point.y} r={3.6} className="ksa-value-dot" />
            ))}
            {axes.map((axis, index) => {
              const angle = -Math.PI / 2 + index * angleStep;
              const labelRadius = radius + 26;
              const x = center + labelRadius * Math.cos(angle);
              const y = center + labelRadius * Math.sin(angle);
              return (
                <text
                  key={`${title}-label-${axis.key}`}
                  x={x}
                  y={y}
                  className="ksa-axis-label"
                  textAnchor={labelAnchorForAngle(angle)}
                  dominantBaseline="middle"
                >
                  {axis.label}
                </text>
              );
            })}
          </g>
        </svg>
      </div>
    </article>
  );
}

export function KsaPanel({
  profile,
  definition,
  attempt,
  drillTopics,
  drillAttempt,
  loading,
  saving,
  error,
  onReload,
  onLoadDefinition,
  onLoadLatestAttempt,
  onStartAssessment,
  onSaveAnswers,
  onCompleteAssessment,
  onLoadDrillTopics,
  onLoadLatestDrillAttempt,
  onStartDrillAttempt,
  onSaveDrillAnswers,
  onCompleteDrillAttempt,
}: KsaPanelProps) {
  const [assessmentDialogOpen, setAssessmentDialogOpen] = useState(false);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [section, setSection] = useState<AssessmentSection>("intro");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [phase1Page, setPhase1Page] = useState(0);
  const [phase1Answers, setPhase1Answers] = useState<Record<string, number>>({});
  const [knowledgeAnswers, setKnowledgeAnswers] = useState<Record<string, string>>({});
  const [skillAnswers, setSkillAnswers] = useState<Record<string, "A" | "B">>({});
  const [abilityAnswers, setAbilityAnswers] = useState<Record<string, { answer: string; response_time_seconds: number }>>({});
  const [abilityStartedAt, setAbilityStartedAt] = useState<number>(Date.now());
  const [nowMs, setNowMs] = useState<number>(Date.now());
  const [sensoryPlaying, setSensoryPlaying] = useState(false);
  const [sensoryError, setSensoryError] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [drillDialogOpen, setDrillDialogOpen] = useState(false);
  const [drillStep, setDrillStep] = useState<"topics" | "questions" | "complete">("topics");
  const [selectedDrillTopicKeys, setSelectedDrillTopicKeys] = useState<string[]>([]);
  const [drillAttemptId, setDrillAttemptId] = useState<string | null>(null);
  const [drillQuestionIndex, setDrillQuestionIndex] = useState(0);
  const [drillAnswers, setDrillAnswers] = useState<Record<string, { answer: string; response_time_seconds: number }>>({});
  const [drillQuestionStartedAt, setDrillQuestionStartedAt] = useState<number>(Date.now());
  const [drillNowMs, setDrillNowMs] = useState<number>(Date.now());
  const [drillLocalError, setDrillLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!assessmentDialogOpen || !attempt?.attempt_id) {
      return;
    }
    setAttemptId(attempt.attempt_id);
    const answers = (attempt.answers ?? {}) as Record<string, unknown>;
    const phase1 = (answers.phase1 ?? {}) as Record<string, number>;
    const knowledge = (answers.knowledge ?? {}) as Record<string, string>;
    const skills = (answers.skills ?? {}) as Record<string, "A" | "B">;
    const abilities = (answers.abilities ?? {}) as Record<string, { answer: string; response_time_seconds: number }>;
    if (Object.keys(phase1).length > 0) {
      setPhase1Answers(phase1);
    }
    if (Object.keys(knowledge).length > 0) {
      setKnowledgeAnswers(knowledge);
    }
    if (Object.keys(skills).length > 0) {
      setSkillAnswers(skills);
    }
    if (Object.keys(abilities).length > 0) {
      setAbilityAnswers(abilities);
    }
  }, [assessmentDialogOpen, attempt?.attempt_id, attempt?.answers]);

  useEffect(() => {
    if (!drillDialogOpen || !drillAttempt?.attempt_id) {
      return;
    }
    setDrillAttemptId(drillAttempt.attempt_id);
    const answers = (drillAttempt.answers ?? {}) as Record<string, { answer?: string; response_time_seconds?: number }>;
    if (Object.keys(answers).length > 0) {
      const normalized: Record<string, { answer: string; response_time_seconds: number }> = {};
      for (const [key, value] of Object.entries(answers)) {
        normalized[key] = {
          answer: String(value?.answer ?? ""),
          response_time_seconds: Number(value?.response_time_seconds ?? 0),
        };
      }
      setDrillAnswers(normalized);
    }
  }, [drillDialogOpen, drillAttempt?.attempt_id, drillAttempt?.answers]);

  const sliderValues = useMemo(() => {
    const map: Record<string, number> = {};
    for (const slider of definition?.phase1_sliders ?? []) {
      map[slider.key] = phase1Answers[slider.key] ?? 1;
    }
    return map;
  }, [definition?.phase1_sliders, phase1Answers]);

  const triggeredKnowledgeTopics = useMemo(() => {
    const enabled = new Set<string>();
    for (const group of KNOWLEDGE_GROUPS) {
      if ((sliderValues[group.sliderKey] ?? 1) > 5) {
        for (const topic of group.topics) {
          enabled.add(topic);
        }
      }
    }
    return enabled;
  }, [sliderValues]);

  const triggeredSkillTopics = useMemo(() => {
    const enabled = new Set<string>();
    for (const group of SKILL_GROUPS) {
      if ((sliderValues[group.sliderKey] ?? 1) > 5) {
        for (const topic of group.topics) {
          enabled.add(topic);
        }
      }
    }
    return enabled;
  }, [sliderValues]);

  const knowledgeQueue = useMemo(
    () => (definition?.knowledge_questions ?? []).filter((item) => triggeredKnowledgeTopics.has(item.topic)),
    [definition?.knowledge_questions, triggeredKnowledgeTopics],
  );
  const skillQueue = useMemo(
    () => (definition?.skill_questions ?? []).filter((item) => triggeredSkillTopics.has(item.topic)),
    [definition?.skill_questions, triggeredSkillTopics],
  );
  const abilityQueue = definition?.ability_questions ?? [];
  const totalQuestions = (definition?.phase1_sliders.length ?? 0) + knowledgeQueue.length + skillQueue.length + abilityQueue.length;
  const phase1Sliders = definition?.phase1_sliders ?? [];
  const phase1PageCount = Math.max(1, Math.ceil(phase1Sliders.length / PHASE1_PAGE_SIZE));
  const phase1PageItems = phase1Sliders.slice(phase1Page * PHASE1_PAGE_SIZE, (phase1Page + 1) * PHASE1_PAGE_SIZE);

  const completedQuestions = useMemo(() => {
    if (!definition) {
      return 0;
    }
    if (section === "intro") {
      return 0;
    }
    if (section === "phase1") {
      return Math.min((phase1Page + 1) * PHASE1_PAGE_SIZE, definition.phase1_sliders.length);
    }
    if (section === "knowledge") {
      return definition.phase1_sliders.length + questionIndex;
    }
    if (section === "skills") {
      return definition.phase1_sliders.length + knowledgeQueue.length + questionIndex;
    }
    if (section === "abilities") {
      return definition.phase1_sliders.length + knowledgeQueue.length + skillQueue.length + questionIndex;
    }
    return totalQuestions;
  }, [definition, section, phase1Answers, knowledgeQueue.length, skillQueue.length, questionIndex, totalQuestions]);

  const progressPercent = totalQuestions === 0 ? 0 : Math.min(100, Math.round((completedQuestions / totalQuestions) * 100));
  const abilityTimeLimitSeconds = definition?.time_limit_seconds ?? 30;
  const abilityRemainingSeconds = Math.max(0, abilityTimeLimitSeconds - Math.floor((nowMs - abilityStartedAt) / 1000));
  const drillQuestionSet: KsaDrillQuestion[] = drillAttempt?.question_set ?? [];
  const currentDrillQuestion = drillQuestionSet[drillQuestionIndex];
  const drillQuestionTimeLimit = currentDrillQuestion?.time_limit_seconds ?? null;
  const drillRemainingSeconds = drillQuestionTimeLimit == null
    ? null
    : Math.max(0, drillQuestionTimeLimit - Math.floor((drillNowMs - drillQuestionStartedAt) / 1000));
  const drillProgressPercent = drillQuestionSet.length === 0 ? 0 : Math.min(100, Math.round(((drillQuestionIndex + 1) / drillQuestionSet.length) * 100));

  useEffect(() => {
    if (!assessmentDialogOpen || section !== "abilities") {
      return;
    }
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 500);
    return () => window.clearInterval(timer);
  }, [assessmentDialogOpen, section]);

  useEffect(() => {
    if (section === "abilities") {
      setAbilityStartedAt(Date.now());
      setNowMs(Date.now());
    }
  }, [section, questionIndex]);

  useEffect(() => {
    if (!drillDialogOpen || drillStep !== "questions") {
      return;
    }
    const timer = window.setInterval(() => {
      setDrillNowMs(Date.now());
    }, 500);
    return () => window.clearInterval(timer);
  }, [drillDialogOpen, drillStep]);

  useEffect(() => {
    if (drillStep === "questions") {
      setDrillQuestionStartedAt(Date.now());
      setDrillNowMs(Date.now());
    }
  }, [drillStep, drillQuestionIndex]);

  async function openAssessment() {
    setAssessmentDialogOpen(true);
    setSection("intro");
    setQuestionIndex(0);
    setPhase1Page(0);
    setLocalError(null);
    try {
      if (!definition) {
        await onLoadDefinition();
      }
      await onLoadLatestAttempt();
    } catch (openError) {
      setLocalError(openError instanceof Error ? openError.message : "Failed to prepare assessment");
    }
  }

  async function openDrills() {
    setDrillDialogOpen(true);
    setDrillStep("topics");
    setSelectedDrillTopicKeys([]);
    setDrillAttemptId(null);
    setDrillQuestionIndex(0);
    setDrillAnswers({});
    setDrillLocalError(null);
    try {
      if (drillTopics.length === 0) {
        await onLoadDrillTopics();
      }
      await onLoadLatestDrillAttempt();
    } catch (loadError) {
      setDrillLocalError(loadError instanceof Error ? loadError.message : "Failed to prepare drill assessment");
    }
  }

  function resetAssessmentState() {
    setSection("intro");
    setQuestionIndex(0);
    setPhase1Page(0);
    setLocalError(null);
    setAttemptId(null);
    setPhase1Answers({});
    setKnowledgeAnswers({});
    setSkillAnswers({});
    setAbilityAnswers({});
  }

  function closeAssessment() {
    setAssessmentDialogOpen(false);
    resetAssessmentState();
  }

  function closeDrills() {
    setDrillDialogOpen(false);
    setDrillStep("topics");
    setSelectedDrillTopicKeys([]);
    setDrillAttemptId(null);
    setDrillQuestionIndex(0);
    setDrillAnswers({});
    setDrillLocalError(null);
  }

  async function persistDraftAnswers() {
    if (!attemptId) {
      return;
    }
    await onSaveAnswers(attemptId, {
      phase1: phase1Answers,
      knowledge: knowledgeAnswers,
      skills: skillAnswers,
      abilities: abilityAnswers,
    });
  }

  async function startFlow() {
    setLocalError(null);
    try {
      const started = (await onStartAssessment()) as { attempt_id?: string } | null;
      const startedAttemptId = started?.attempt_id ?? attempt?.attempt_id ?? null;
      setAttemptId(startedAttemptId);
      setSection("phase1");
      setPhase1Page(0);
    } catch (startError) {
      setLocalError(startError instanceof Error ? startError.message : "Failed to start assessment");
    }
  }

  function nextAfterPhase1() {
    if (!definition) {
      return;
    }
    setLocalError(null);
    if (knowledgeQueue.length > 0) {
      setSection("knowledge");
      setQuestionIndex(0);
      return;
    }
    if (skillQueue.length > 0) {
      setSection("skills");
      setQuestionIndex(0);
      return;
    }
    setSection("abilities");
    setQuestionIndex(0);
  }

  async function handleKnowledgeNext() {
    const current = knowledgeQueue[questionIndex];
    if (!current) {
      return;
    }
    if (!knowledgeAnswers[current.id]) {
      setLocalError("Select an answer to continue.");
      return;
    }
    setLocalError(null);
    if (questionIndex + 1 < knowledgeQueue.length) {
      setQuestionIndex((value) => value + 1);
      return;
    }
    await persistDraftAnswers();
    if (skillQueue.length > 0) {
      setSection("skills");
      setQuestionIndex(0);
      return;
    }
    setSection("abilities");
    setQuestionIndex(0);
  }

  async function handleSkillsNext() {
    const current = skillQueue[questionIndex];
    if (!current) {
      return;
    }
    if (!skillAnswers[current.id]) {
      setLocalError("Choose one option to continue.");
      return;
    }
    setLocalError(null);
    if (questionIndex + 1 < skillQueue.length) {
      setQuestionIndex((value) => value + 1);
      return;
    }
    await persistDraftAnswers();
    setSection("abilities");
    setQuestionIndex(0);
  }

  async function handleAbilitiesNext() {
    const current = abilityQueue[questionIndex];
    if (!current) {
      return;
    }
    const currentResponseSeconds = Math.min(
      abilityTimeLimitSeconds,
      Math.max(0, (Date.now() - abilityStartedAt) / 1000),
    );
    const existing = abilityAnswers[current.id];
    if (!existing || !existing.answer.trim()) {
      setLocalError("Enter an answer to continue.");
      return;
    }
    const nextAbilities = {
      ...abilityAnswers,
      [current.id]: {
        answer: existing.answer,
        response_time_seconds: currentResponseSeconds,
      },
    };
    setAbilityAnswers(nextAbilities);
    setLocalError(null);
    if (questionIndex + 1 < abilityQueue.length) {
      setQuestionIndex((value) => value + 1);
      return;
    }
    if (attemptId) {
      await onSaveAnswers(attemptId, {
        phase1: phase1Answers,
        knowledge: knowledgeAnswers,
        skills: skillAnswers,
        abilities: nextAbilities,
      });
    }
    if (!attemptId) {
      setLocalError("Assessment attempt not found. Please restart.");
      return;
    }
    await onCompleteAssessment(attemptId);
    await onReload();
    setSection("complete");
  }

  async function playSensoryTones() {
    if (sensoryPlaying) {
      return;
    }
    setSensoryError(null);
    setSensoryPlaying(true);
    try {
      const AudioContextCtor = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextCtor) {
        throw new Error("Audio playback is not supported in this browser.");
      }
      const audioContext = new AudioContextCtor();
      const scheduleTone = (frequency: number, startAt: number, durationSeconds = 0.45) => {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.type = "sine";
        oscillator.frequency.value = frequency;
        gainNode.gain.setValueAtTime(0.0001, startAt);
        gainNode.gain.exponentialRampToValueAtTime(0.18, startAt + 0.02);
        gainNode.gain.exponentialRampToValueAtTime(0.0001, startAt + durationSeconds);
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        oscillator.start(startAt);
        oscillator.stop(startAt + durationSeconds + 0.02);
      };
      const now = audioContext.currentTime + 0.08;
      scheduleTone(880, now); // High
      scheduleTone(554.37, now + 0.62); // Mid
      scheduleTone(392, now + 1.24); // Low
      await new Promise((resolve) => window.setTimeout(resolve, 2200));
      void audioContext.close();
    } catch (playError) {
      setSensoryError(playError instanceof Error ? playError.message : "Unable to play tones.");
    } finally {
      setSensoryPlaying(false);
    }
  }

  function toggleDrillTopic(topicKey: string) {
    setSelectedDrillTopicKeys((current) => {
      if (current.includes(topicKey)) {
        return current.filter((item) => item !== topicKey);
      }
      if (current.length >= 3) {
        return current;
      }
      return [...current, topicKey];
    });
  }

  async function startDrillFlow() {
    if (selectedDrillTopicKeys.length < 1 || selectedDrillTopicKeys.length > 3) {
      setDrillLocalError("Choose between 1 and 3 topics.");
      return;
    }
    setDrillLocalError(null);
    try {
      const started = (await onStartDrillAttempt(selectedDrillTopicKeys)) as { attempt_id?: string } | null;
      const nextAttemptId = started?.attempt_id ?? drillAttempt?.attempt_id ?? null;
      setDrillAttemptId(nextAttemptId);
      setDrillQuestionIndex(0);
      setDrillStep("questions");
    } catch (startError) {
      setDrillLocalError(startError instanceof Error ? startError.message : "Failed to start drill assessment");
    }
  }

  async function saveDrillDraft(nextAnswers?: Record<string, { answer: string; response_time_seconds: number }>) {
    const id = drillAttemptId ?? drillAttempt?.attempt_id ?? null;
    if (!id) {
      return;
    }
    await onSaveDrillAnswers(id, nextAnswers ?? drillAnswers);
  }

  async function handleDrillNext() {
    const question = currentDrillQuestion;
    if (!question) {
      return;
    }
    const existing = drillAnswers[question.id];
    if (!existing || !existing.answer.trim()) {
      setDrillLocalError("Enter an answer to continue.");
      return;
    }
    const elapsedSeconds = Math.max(0, (Date.now() - drillQuestionStartedAt) / 1000);
    const responseSeconds = question.time_limit_seconds != null ? Math.min(question.time_limit_seconds, elapsedSeconds) : elapsedSeconds;
    const nextAnswers = {
      ...drillAnswers,
      [question.id]: {
        answer: existing.answer,
        response_time_seconds: responseSeconds,
      },
    };
    setDrillAnswers(nextAnswers);
    setDrillLocalError(null);
    if (drillQuestionIndex + 1 < drillQuestionSet.length) {
      setDrillQuestionIndex((value) => value + 1);
      return;
    }
    await saveDrillDraft(nextAnswers);
    const id = drillAttemptId ?? drillAttempt?.attempt_id ?? null;
    if (!id) {
      setDrillLocalError("Drill attempt not found. Please restart.");
      return;
    }
    await onCompleteDrillAttempt(id);
    await onReload();
    setDrillStep("complete");
  }

  const currentKnowledgeQuestion = knowledgeQueue[questionIndex];
  const currentSkillQuestion = skillQueue[questionIndex];
  const currentAbilityQuestion = abilityQueue[questionIndex];
  const isSensoryQuestion = currentAbilityQuestion?.id === "A.5";

  return (
    <>
      <section className="info-group-card learning-path-details-card ksa-map-card">
        <div className="ksa-map-head">
          <div className="learning-path-details-header">
            <h4>Knowledge, Skills, and Abilities</h4>
            <p>Your KSA big-map gives a first view across foundational domains, practical capability, and cognitive execution.</p>
            <div className="ksa-global-legend" aria-label="Global Dreyfus legend">
              {DREYFUS_LEVELS.map((item, index) => (
                <span key={item}>
                  <i>{index + 1}</i>
                  {item}
                </span>
              ))}
            </div>
          </div>
          <button className="restart-button library-upload-button" type="button" onClick={() => void openAssessment()}>
            Start Assessment
          </button>
        </div>

        {loading ? <div className="empty-state">Loading KSA profile...</div> : null}
        {!loading && error ? (
          <div className="empty-state">
            <div>
              <p>{error}</p>
              <button className="secondary-button" type="button" onClick={onReload}>
                Retry
              </button>
            </div>
          </div>
        ) : null}

        {!loading && !error && profile ? (
          <div className="ksa-radar-grid">
            <RadarPanel title="Knowledge" subtitle="The Mental Library" axes={KNOWLEDGE_AXES} values={toRecord(profile.knowledge)} />
            <RadarPanel title="Skills" subtitle="The Toolbox" axes={SKILLS_AXES} values={toRecord(profile.skills)} />
            <RadarPanel title="Abilities" subtitle="The Engine" axes={ABILITIES_AXES} values={toRecord(profile.abilities)} />
          </div>
        ) : null}
      </section>

      <section className="info-group-card ksa-deep-dive-card">
        <div className="learning-path-details-header">
          <h4>KSA Deep Dive</h4>
          <p>This section will expand into subdomain diagnostics, trend lines, and targeted recommendations in the next step.</p>
        </div>
        <div className="ksa-deep-dive-grid">
          <article>
            <h5>Knowledge Breakdown</h5>
            <p>Placeholder: topic-level distribution, strengths, and weakest clusters will appear here.</p>
          </article>
          <article>
            <h5>Skills Breakdown</h5>
            <p>Placeholder: applied skill clusters and practical readiness checks will appear here.</p>
          </article>
          <article>
            <h5>Abilities Breakdown</h5>
            <p>Placeholder: cognitive and social-executive subdimensions will appear here.</p>
          </article>
        </div>
        <div className="table-footer-actions">
          <button className="primary-button" type="button" onClick={() => void openDrills()}>
            Start Assessment Drills
          </button>
        </div>
      </section>

      {drillDialogOpen ? (
        <Dialog
          title="KSA Assessment Drills"
          onClose={saving ? () => undefined : closeDrills}
          className="diagnostic-dialog ksa-assessment-dialog"
          contentClassName="diagnostic-dialog-content"
          bodyClassName="diagnostic-dialog-body"
          actions={
            <>
              <button className="secondary-button" type="button" onClick={closeDrills} disabled={saving}>
                Cancel
              </button>
              {drillStep === "topics" ? (
                <button className="primary-button" type="button" onClick={() => void startDrillFlow()} disabled={saving || selectedDrillTopicKeys.length < 1}>
                  Start Drills
                </button>
              ) : null}
              {drillStep === "questions" ? (
                <button className="primary-button" type="button" onClick={() => void handleDrillNext()} disabled={saving}>
                  {drillQuestionIndex + 1 >= drillQuestionSet.length ? "Finish Drills" : "Continue"}
                </button>
              ) : null}
              {drillStep === "complete" ? (
                <button className="primary-button" type="button" onClick={closeDrills}>
                  Done
                </button>
              ) : null}
            </>
          }
        >
          <div className="ksa-assessment-flow">
            {drillStep === "topics" ? (
              <div className="ksa-drill-topics">
                <h3>Select Drill Topics</h3>
                <p>Choose 1 to 3 big-map topics. Each selected topic runs a 12-question triple-drill sequence.</p>
                <div className="ksa-drill-topic-grid">
                  {(drillTopics ?? []).map((topic) => {
                    const selected = selectedDrillTopicKeys.includes(topic.key);
                    return (
                      <button
                        key={topic.key}
                        type="button"
                        className={`ksa-drill-topic-card${selected ? " selected" : ""}`}
                        onClick={() => toggleDrillTopic(topic.key)}
                      >
                        <strong>{topic.name}</strong>
                        <small>{topic.group.toUpperCase()}</small>
                        <span>{topic.subtopics.slice(0, 3).join(" · ")}</span>
                      </button>
                    );
                  })}
                </div>
                <p className="ksa-drill-topic-meta">{selectedDrillTopicKeys.length} of 3 selected</p>
              </div>
            ) : null}

            {drillStep === "questions" && currentDrillQuestion ? (
              <div className="ksa-question-card">
                <div className="diagnostic-question-progress">
                  <span style={{ width: `${drillProgressPercent}%` }} />
                </div>
                <p className="ksa-assessment-progress-label">
                  {drillQuestionIndex + 1} / {drillQuestionSet.length} completed
                </p>
                <div className="ksa-drill-question-meta">
                  <span>{currentDrillQuestion.topic_name}</span>
                  <span>{currentDrillQuestion.block_label}</span>
                  <span>{currentDrillQuestion.kind.replace("_", " ")}</span>
                </div>
                {drillQuestionTimeLimit != null ? (
                  <p className="ksa-ability-timer">Time target: {drillQuestionTimeLimit}s | Remaining: {drillRemainingSeconds ?? 0}s</p>
                ) : null}
                <p>{currentDrillQuestion.prompt}</p>
                <textarea
                  className="dialog-input diagnostic-textarea"
                  rows={4}
                  placeholder="Enter your answer"
                  value={drillAnswers[currentDrillQuestion.id]?.answer ?? ""}
                  onChange={(event) =>
                    setDrillAnswers((current) => ({
                      ...current,
                      [currentDrillQuestion.id]: {
                        answer: event.target.value,
                        response_time_seconds: drillQuestionTimeLimit != null
                          ? Math.min(drillQuestionTimeLimit, Math.max(0, (Date.now() - drillQuestionStartedAt) / 1000))
                          : Math.max(0, (Date.now() - drillQuestionStartedAt) / 1000),
                      },
                    }))
                  }
                />
              </div>
            ) : null}

            {drillStep === "complete" ? (
              <div className="diagnostic-intro ksa-assessment-placeholder">
                <h3>Drill Assessment Completed</h3>
                <p>Your KSA map has been refined with deep-dive drill results and sub-topic progression updates.</p>
              </div>
            ) : null}

            {drillLocalError ? <p className="inline-error">{drillLocalError}</p> : null}
            {error ? <p className="inline-error">{error}</p> : null}
          </div>
        </Dialog>
      ) : null}

      {assessmentDialogOpen ? (
        <Dialog
          title="KSA Assessment"
          onClose={saving ? () => undefined : closeAssessment}
          className="diagnostic-dialog ksa-assessment-dialog"
          contentClassName="diagnostic-dialog-content"
          bodyClassName="diagnostic-dialog-body"
          actions={
            <>
              <button className="secondary-button" type="button" onClick={closeAssessment} disabled={saving}>
                Cancel
              </button>
              {section === "intro" ? (
                <button className="primary-button" type="button" onClick={() => void startFlow()} disabled={saving}>
                  Start Assessment
                </button>
              ) : null}
              {section === "phase1" ? (
                <>
                  {phase1Page > 0 ? (
                    <button className="secondary-button" type="button" onClick={() => setPhase1Page((value) => Math.max(0, value - 1))} disabled={saving}>
                      Back
                    </button>
                  ) : null}
                  {phase1Page + 1 < phase1PageCount ? (
                    <button className="primary-button" type="button" onClick={() => setPhase1Page((value) => Math.min(phase1PageCount - 1, value + 1))} disabled={saving}>
                      Next
                    </button>
                  ) : (
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => {
                        void persistDraftAnswers().then(() => nextAfterPhase1()).catch((err: unknown) => {
                          setLocalError(err instanceof Error ? err.message : "Failed to save answers");
                        });
                      }}
                      disabled={saving}
                    >
                      Continue
                    </button>
                  )}
                </>
              ) : null}
              {section === "knowledge" ? (
                <button className="primary-button" type="button" onClick={() => void handleKnowledgeNext()} disabled={saving}>
                  Continue
                </button>
              ) : null}
              {section === "skills" ? (
                <button className="primary-button" type="button" onClick={() => void handleSkillsNext()} disabled={saving}>
                  Continue
                </button>
              ) : null}
              {section === "abilities" ? (
                <button className="primary-button" type="button" onClick={() => void handleAbilitiesNext()} disabled={saving}>
                  {questionIndex + 1 >= abilityQueue.length ? "Finish Assessment" : "Continue"}
                </button>
              ) : null}
              {section === "complete" ? (
                <button className="primary-button" type="button" onClick={closeAssessment}>
                  Done
                </button>
              ) : null}
            </>
          }
        >
          <div className="ksa-assessment-flow">
            {section !== "intro" && section !== "complete" ? (
              <div className="diagnostic-question-progress">
                <span style={{ width: `${progressPercent}%` }} />
              </div>
            ) : null}
            {section !== "intro" && section !== "complete" ? (
              <p className="ksa-assessment-progress-label">
                {completedQuestions} / {totalQuestions} completed
              </p>
            ) : null}
            {localError ? <p className="inline-error">{localError}</p> : null}
            {error ? <p className="inline-error">{error}</p> : null}

            {section === "intro" ? (
              <div className="diagnostic-intro ksa-assessment-placeholder ksa-assessment-intro">
                <h3>Welcome to Your KSA Assessment</h3>
                <p>This guided check helps us build your first real Knowledge, Skills, and Abilities map.</p>
                <div className="ksa-assessment-intro-notes">
                  <p>What to expect: about 6-8 minutes, one question at a time, and no trick questions.</p>
                  <p>Outcome: your answers are scored and saved, then your big-map updates with real results.</p>
                </div>
                <div className="diagnostic-intro-cards">
                  <article>
                    <h4>Phase 1: Broad Sieve</h4>
                    <p>Short sliders help us focus on areas that are most relevant for your first run.</p>
                  </article>
                  <article>
                    <h4>Phase 2/3: Knowledge + Skills</h4>
                    <p>Knowledge checks verify basics. Skills scenarios evaluate practical decision quality.</p>
                  </article>
                  <article>
                    <h4>Phase 4: Abilities</h4>
                    <p>Short timed prompts measure core capacity using correctness and response speed.</p>
                  </article>
                </div>
              </div>
            ) : null}

            {section === "phase1" ? (
              <div className="ksa-phase-grid">
                <p className="ksa-phase-page-label">Phase 1 of 4 - Sieve Questions (page {phase1Page + 1} of {phase1PageCount})</p>
                {phase1PageItems.map((slider) => {
                  const min = Number(slider.min);
                  const max = Number(slider.max);
                  const value = sliderValues[slider.key] ?? min;
                  const fillPercent = ((value - min) / Math.max(max - min, 1)) * 100;
                  const marks = Array.from({ length: Math.max(0, max - min + 1) }, (_, index) => min + index);
                  return (
                  <label key={slider.id} className="ksa-slider-card">
                    <strong>{slider.topic}</strong>
                    <span>{slider.prompt}</span>
                    <div className="diagnostic-range-wrap">
                      <input
                        type="range"
                        min={slider.min}
                        max={slider.max}
                        value={value}
                        style={{ "--range-fill": `${fillPercent}%` } as CSSProperties}
                        onChange={(event) =>
                          setPhase1Answers((current) => ({
                            ...current,
                            [slider.key]: Number(event.target.value),
                          }))
                        }
                      />
                      <div className="diagnostic-range-marks" aria-hidden="true">
                        {marks.map((mark) => <span key={`${slider.id}-${mark}`}>{mark}</span>)}
                      </div>
                      <small>Value: {value}</small>
                    </div>
                  </label>
                );
                })}
              </div>
            ) : null}

            {section === "knowledge" && currentKnowledgeQuestion ? (
              <div className="ksa-question-card">
                <h4>Knowledge Check</h4>
                <p>{currentKnowledgeQuestion.question}</p>
                <div className="diagnostic-options-list">
                  {currentKnowledgeQuestion.options.map((option) => (
                    <label key={option} className={`diagnostic-option-card${knowledgeAnswers[currentKnowledgeQuestion.id] === option ? " selected" : ""}`}>
                      <input
                        type="radio"
                        name={currentKnowledgeQuestion.id}
                        checked={knowledgeAnswers[currentKnowledgeQuestion.id] === option}
                        onChange={() =>
                          setKnowledgeAnswers((current) => ({
                            ...current,
                            [currentKnowledgeQuestion.id]: option,
                          }))
                        }
                      />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </div>
            ) : null}

            {section === "skills" && currentSkillQuestion ? (
              <div className="ksa-question-card">
                <h4>Skill Simulation</h4>
                <p>{currentSkillQuestion.scenario}</p>
                <div className="diagnostic-options-list">
                  <label className={`diagnostic-option-card${skillAnswers[currentSkillQuestion.id] === "A" ? " selected" : ""}`}>
                    <input
                      type="radio"
                      name={currentSkillQuestion.id}
                      checked={skillAnswers[currentSkillQuestion.id] === "A"}
                      onChange={() =>
                        setSkillAnswers((current) => ({
                          ...current,
                          [currentSkillQuestion.id]: "A",
                        }))
                      }
                    />
                    <span>{currentSkillQuestion.choice_a}</span>
                  </label>
                  <label className={`diagnostic-option-card${skillAnswers[currentSkillQuestion.id] === "B" ? " selected" : ""}`}>
                    <input
                      type="radio"
                      name={currentSkillQuestion.id}
                      checked={skillAnswers[currentSkillQuestion.id] === "B"}
                      onChange={() =>
                        setSkillAnswers((current) => ({
                          ...current,
                          [currentSkillQuestion.id]: "B",
                        }))
                      }
                    />
                    <span>{currentSkillQuestion.choice_b}</span>
                  </label>
                </div>
              </div>
            ) : null}

            {section === "abilities" && currentAbilityQuestion ? (
              <div className="ksa-question-card">
                <div className="ksa-ability-head">
                  <h4>Ability Engine</h4>
                  <span className="ksa-ability-timer">Time target: {abilityTimeLimitSeconds}s | Remaining: {abilityRemainingSeconds}s</span>
                </div>
                <p>{currentAbilityQuestion.task}</p>
                {isSensoryQuestion ? (
                  <div className="ksa-sensory-controls">
                    <button className="secondary-button" type="button" onClick={() => void playSensoryTones()} disabled={sensoryPlaying}>
                      {sensoryPlaying ? "Playing..." : "Play High / Mid / Low Tones"}
                    </button>
                    <small>Listen carefully and enter which tone was second.</small>
                    {sensoryError ? <p className="inline-error">{sensoryError}</p> : null}
                  </div>
                ) : null}
                <textarea
                  className="dialog-input diagnostic-textarea"
                  rows={3}
                  placeholder={currentAbilityQuestion.open_ended ? "Enter 3 distinct uses, separated by commas" : "Enter your answer"}
                  value={abilityAnswers[currentAbilityQuestion.id]?.answer ?? ""}
                  onChange={(event) =>
                    setAbilityAnswers((current) => ({
                      ...current,
                      [currentAbilityQuestion.id]: {
                        answer: event.target.value,
                        response_time_seconds: Math.min(
                          abilityTimeLimitSeconds,
                          Math.max(0, (Date.now() - abilityStartedAt) / 1000),
                        ),
                      },
                    }))
                  }
                />
              </div>
            ) : null}

            {section === "complete" ? (
              <div className="diagnostic-intro ksa-assessment-placeholder">
                <h3>Assessment Completed</h3>
                <p>Your KSA profile has been scored and persisted. The radar visualization now reflects your real assessment results.</p>
              </div>
            ) : null}
          </div>
        </Dialog>
      ) : null}
    </>
  );
}
