import { Check, Search, X } from "lucide-react";
import { useMemo, useState } from "react";


export function KnowledgePointPicker({ points = [], selected = [], onChange, max = 3 }) {
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const visible = useMemo(() => points.filter((point) => `${point.name}${point.chapter}`.includes(query.trim())), [points, query]);
  const selectedPoints = selected.map((id) => points.find((point) => point.id === id)).filter(Boolean);

  const toggle = (id) => {
    if (selected.includes(id)) {
      setError("");
      onChange(selected.filter((item) => item !== id));
      return;
    }
    if (selected.length >= max) {
      setError(`每道题最多关联 ${max} 个知识点`);
      return;
    }
    setError("");
    onChange([...selected, id]);
  };

  return (
    <div className="assessmentPicker">
      <div className="assessmentPickerHead">
        <label className="assessmentSearch">
          <Search size={15} />
          <span className="srOnly">搜索知识点</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索知识点名称或章节" />
        </label>
        <strong>已选 {selected.length}/{max}</strong>
      </div>
      {selectedPoints.length > 0 && <div className="assessmentSelectedTags" aria-label="已选知识点">
        {selectedPoints.map((point) => <button key={point.id} type="button" onClick={() => toggle(point.id)} title="移除知识点">
          {point.name}<X size={13} />
        </button>)}
      </div>}
      <div className="assessmentOptionList" role="listbox" aria-label="可选知识点" aria-multiselectable="true">
        {visible.map((point) => {
          const active = selected.includes(point.id);
          return <button key={point.id} type="button" role="option" aria-selected={active} onClick={() => toggle(point.id)}>
            <span><strong>{point.name}</strong><small>{point.chapter || "未分章"} · {point.questionCount || 0} 道题</small></span>
            {active && <Check size={16} />}
          </button>;
        })}
        {!visible.length && <p className="assessmentInlineEmpty">没有匹配的知识点</p>}
      </div>
      {error && <p className="assessmentFieldError" role="alert">{error}</p>}
    </div>
  );
}
