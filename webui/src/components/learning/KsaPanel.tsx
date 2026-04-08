import { useMemo, useState } from "react";
import type { KSAAbilities, KSAKnowledge, KSAProfile, KSASkills, KSAValue } from "../../types/chat";
import { Dialog } from "../common/Dialog";

type KsaPanelProps = {
  profile: KSAProfile | null;
  loading: boolean;
  error: string | null;
  onReload: () => void;
};

type RadarAxis = {
  key: string;
  label: string;
};

const DREYFUS_LEVELS = ["Novice", "Advanced", "Competent", "Proficient", "Expert"];

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
      angle,
      label: axis.label,
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
      <ul className="ksa-ring-legend">
        {DREYFUS_LEVELS.map((level, index) => (
          <li key={`${title}-level-${level}`}>
            <span>{index + 1}</span>
            {level}
          </li>
        ))}
      </ul>
    </article>
  );
}

function toRecord(values: KSAKnowledge | KSASkills | KSAAbilities): Record<string, KSAValue> {
  return values as unknown as Record<string, KSAValue>;
}

export function KsaPanel({ profile, loading, error, onReload }: KsaPanelProps) {
  const [assessmentDialogOpen, setAssessmentDialogOpen] = useState(false);
  const baselineLabel = profile?.profile_source === "student_default_baseline" ? "Baseline profile (no assessment yet)" : "Baseline profile";

  return (
    <>
      <section className="info-group-card learning-path-details-card ksa-map-card">
        <div className="ksa-map-head">
          <div className="learning-path-details-header">
            <h4>Knowledge, Skills, and Abilities</h4>
            <p>Your KSA big-map gives a first view across foundational domains, practical capability, and cognitive execution.</p>
            <div className="learning-path-details-meta">
              <span>1 Novice</span>
              <span>2 Advanced</span>
              <span>3 Competent</span>
              <span>4 Proficient</span>
              <span>5 Expert</span>
            </div>
          </div>
          <button className="restart-button library-upload-button" type="button" onClick={() => setAssessmentDialogOpen(true)}>
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
      </section>

      {assessmentDialogOpen ? (
        <Dialog
          title="KSA Assessment"
          onClose={() => setAssessmentDialogOpen(false)}
          className="diagnostic-dialog ksa-assessment-dialog"
          contentClassName="diagnostic-dialog-content"
          bodyClassName="diagnostic-dialog-body"
          actions={
            <>
              <button className="secondary-button" type="button" onClick={() => setAssessmentDialogOpen(false)}>
                Close
              </button>
            </>
          }
        >
          <div className="diagnostic-intro ksa-assessment-placeholder">
            <h3>KSA Assessment Coming Soon</h3>
            <p>This dialog intentionally ships as a placeholder shell in this step. The full assessment workflow will be added next.</p>
            <div className="diagnostic-intro-cards">
              <article>
                <h4>Knowledge</h4>
                <p>Future prompt sets will score foundational and domain knowledge on the same Dreyfus 1-5 scale.</p>
              </article>
              <article>
                <h4>Skills</h4>
                <p>Future practical scenarios will measure applied execution and evidence-backed competency.</p>
              </article>
              <article>
                <h4>Abilities</h4>
                <p>Future adaptive sections will estimate reasoning, executive, spatial, and social-emotional capacity.</p>
              </article>
            </div>
          </div>
        </Dialog>
      ) : null}
    </>
  );
}
