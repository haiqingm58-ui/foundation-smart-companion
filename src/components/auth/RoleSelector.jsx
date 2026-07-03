const roles = [
  { id: "student", label: "学生", emoji: "🧑‍🎓" },
  { id: "teacher", label: "指导老师", emoji: "🧑‍🏫" },
  { id: "admin", label: "管理员", emoji: "🛡️" },
];


export function RoleSelector({ value, onChange }) {
  return (
    <div className="roleSelector" role="radiogroup" aria-label="登录角色">
      {roles.map((role) => (
        <button
          key={role.id}
          type="button"
          role="radio"
          aria-checked={value === role.id}
          className={value === role.id ? "selected" : ""}
          onClick={() => onChange(role.id)}
        >
          <span className="roleEmoji" aria-hidden="true">{role.emoji}</span>
          <span>{role.label}</span>
        </button>
      ))}
    </div>
  );
}
