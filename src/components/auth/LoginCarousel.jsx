import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import foundationSection from "../../assets/foundation-section-compact.png";


const base = import.meta.env.BASE_URL || "/";
const slides = [
  { image: foundationSection, title: "基础工程教材学习", desc: "围绕教材章节、公式和工程图表开展系统学习" },
  { image: `${base}knowledge/images/ca562cdd3e6d23207f61bf14ef8cf027a2f36c44c771c2b22af7452de9a80c9a.jpg`, title: "地基与基础结构", desc: "从基础平面布置理解荷载路径与结构选型" },
  { image: `${base}knowledge/images/289641f4f88311e553daed7bff6a20643ff350053dccfda9591dd2b74349c41c.jpg`, title: "桩基础工程", desc: "结合土层剖面分析桩侧阻力与桩端阻力" },
  { image: `${base}knowledge/images/ac092940807daffb9ede0f4f970f11f385e28d64ceec9d57b22499b7e94c33f5.jpg`, title: "工程知识图谱", desc: "串联章节、知识点、公式、案例与规范依据" },
  { image: `${base}knowledge/images/d9adeef00a756850a98e45a2d4b9b2f5de6f5b977c61f61a62f2fc8d14adf22b.jpg`, title: "AI 智能问答", desc: "基于教材与教师资料检索，回答有出处可追溯" },
  { image: `${base}knowledge/images/aec2e30f92bd6e26f668fcb09f143a8f28bb3c090a4394d6c4cd3d6f46fb5cff.jpg`, title: "教师教学管理", desc: "管理班级、题库、作业与学生学习进展" },
];


export function LoginCarousel() {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [failed, setFailed] = useState({});
  const touchStart = useRef(null);

  useEffect(() => {
    if (paused) return undefined;
    const interval = window.setInterval(() => setActive((value) => (value + 1) % slides.length), 4500);
    return () => window.clearInterval(interval);
  }, [paused]);

  function move(offset) {
    setActive((value) => (value + offset + slides.length) % slides.length);
  }

  function onTouchEnd(event) {
    if (touchStart.current === null) return;
    const delta = event.changedTouches[0].clientX - touchStart.current;
    if (Math.abs(delta) > 45) move(delta > 0 ? -1 : 1);
    touchStart.current = null;
  }

  return (
    <section
      className="loginCarousel"
      aria-label="平台场景轮播"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
      onTouchStart={(event) => { touchStart.current = event.touches[0].clientX; }}
      onTouchEnd={onTouchEnd}
    >
      <div className="carouselTrack">
        {slides.map((slide, index) => (
          <article className={index === active ? "carouselSlide active" : "carouselSlide"} aria-hidden={index !== active} key={slide.title}>
            {!failed[index] && <img src={slide.image} alt="" onError={() => setFailed((value) => ({ ...value, [index]: true }))} />}
            <div className="carouselTint" />
            <div className="carouselCopy">
              <span>{String(index + 1).padStart(2, "0")}</span>
              <h2>{slide.title}</h2>
              <p>{slide.desc}</p>
            </div>
          </article>
        ))}
      </div>
      <button className="carouselArrow previous" type="button" aria-label="上一张" onClick={() => move(-1)}><ChevronLeft /></button>
      <button className="carouselArrow next" type="button" aria-label="下一张" onClick={() => move(1)}><ChevronRight /></button>
      <div className="carouselDots" aria-label="选择轮播图片">
        {slides.map((slide, index) => (
          <button key={slide.title} type="button" className={index === active ? "active" : ""} aria-label={`查看${slide.title}`} aria-current={index === active ? "true" : undefined} onClick={() => setActive(index)} />
        ))}
      </div>
    </section>
  );
}
