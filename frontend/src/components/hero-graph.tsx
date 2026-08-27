"use client";

import { useEffect, useRef } from "react";

type Node = { label: string; baseX: number; baseY: number; x: number; y: number; phase: number; r: number };

const LABELS = ["Thinking", "Notice", "Wonder", "Try", "Try again", "Check", "Explain", "Understand"];

function layout(label: string, i: number, w: number, h: number): Pick<Node, "baseX" | "baseY"> {
  const angle = (i / LABELS.length) * Math.PI * 2;
  const radius = 150 + (i % 3) * 55;
  return {
    baseX: w * 0.55 + Math.cos(angle) * radius,
    baseY: h * 0.48 + Math.sin(angle) * radius,
  };
}

/**
 * Decorative hero graph tracing the shape of a guided-discovery turn (a
 * student's thinking moving from noticing a problem through to real
 * understanding, with "try again" as a real branch, not a failure state) --
 * not a chart of curriculum subjects.
 */
export function HeroGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let dims = { w: 0, h: 0 };
    function measure() {
      const rect = canvas!.getBoundingClientRect();
      canvas!.width = rect.width * dpr;
      canvas!.height = rect.height * dpr;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      dims = { w: rect.width, h: rect.height };
    }
    measure();

    const nodes: Node[] = LABELS.map((label, i) => ({
      label,
      ...layout(label, i, dims.w, dims.h),
      x: 0,
      y: 0,
      phase: Math.random() * Math.PI * 2,
      r: i === 0 ? 5 : 3.2,
    }));

    const edges: [number, number][] = [];
    for (let i = 0; i < nodes.length; i++) edges.push([0, i === 0 ? 1 : i]);
    edges.push([1, 2], [3, 4], [5, 6]);

    function onResize() {
      measure();
      nodes.forEach((n, i) => Object.assign(n, layout(n.label, i, dims.w, dims.h)));
    }
    window.addEventListener("resize", onResize);

    function goldRgb() {
      return getComputedStyle(document.documentElement).getPropertyValue("--gold-rgb").trim() || "201, 143, 31";
    }

    let t = 0;
    let raf = 0;
    function frame() {
      t += reduceMotion ? 0 : 0.006;
      ctx!.clearRect(0, 0, dims.w, dims.h);
      const rgb = goldRgb();

      nodes.forEach((n) => {
        n.x = n.baseX + Math.cos(t + n.phase) * 8;
        n.y = n.baseY + Math.sin(t + n.phase) * 8;
      });

      ctx!.lineWidth = 1;
      edges.forEach(([a, b]) => {
        ctx!.strokeStyle = `rgba(${rgb}, 0.28)`;
        ctx!.beginPath();
        ctx!.moveTo(nodes[a].x, nodes[a].y);
        ctx!.lineTo(nodes[b].x, nodes[b].y);
        ctx!.stroke();
      });

      nodes.forEach((n, i) => {
        ctx!.beginPath();
        ctx!.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx!.fillStyle = i === 0 ? `rgb(${rgb})` : "rgba(28, 34, 48, 0.5)";
        ctx!.fill();

        ctx!.font = '10px "IBM Plex Mono", monospace';
        ctx!.fillStyle = "rgba(28, 34, 48, 0.45)";
        ctx!.fillText(n.label, n.x + 9, n.y + 3);
      });

      if (!reduceMotion) raf = requestAnimationFrame(frame);
    }
    frame();

    return () => {
      window.removeEventListener("resize", onResize);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute -top-[30px] -right-[90px] hidden h-[580px] w-[580px] max-w-[52vw] opacity-95 lg:block"
    />
  );
}
