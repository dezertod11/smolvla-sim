"""Interactive web teleop: MJPEG streams + keyboard control + model runner via browser."""

import asyncio
import json
import os
import re
import signal
import subprocess
import threading
from pathlib import Path

import cv2
import numpy as np
import rclpy
from aiohttp import web
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray, String

# ──────────────────────────────────────────────────────────────────────────────
# Tasks known in libero_object (task_id 0-9)
# ──────────────────────────────────────────────────────────────────────────────
LIBERO_TASKS = [
    "pick up the alphabet soup and place it in the basket",
    "pick up the cream cheese and place it in the basket",
    "pick up the salad dressing and place it in the basket",
    "pick up the bbq sauce and place it in the basket",
    "pick up the ketchup and place it in the basket",
    "pick up the milk and place it in the basket",
    "pick up the orange juice and place it in the basket",
    "pick up the tomato sauce and place it in the basket",
    "pick up the butter and place it in the basket",
    "pick up the chocolate pudding and place it in the basket",
]

# ──────────────────────────────────────────────────────────────────────────────
# HTML
# ──────────────────────────────────────────────────────────────────────────────
# fmt: off
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LIBERO Teleop</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f0f13; color: #e0e0e0; font-family: 'Segoe UI', monospace; font-size: 13px; }
h1 { text-align: center; padding: 12px; font-size: 17px; letter-spacing: 2px;
     color: #7ec8e3; border-bottom: 1px solid #2a2a3a; }
.layout { display: flex; gap: 14px; padding: 14px; align-items: flex-start; }
/* cameras */
.cameras { display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
.cam-box { background: #1a1a26; border: 1px solid #2a2a3a; border-radius: 7px; padding: 7px; }
.cam-box label { font-size: 10px; color: #666; display: block; margin-bottom: 3px;
                 letter-spacing:1px; }
.cam-box img { display: block; border-radius: 4px; }
/* right panel */
.panel { flex: 1; display: flex; flex-direction: column; gap: 10px; min-width: 340px; }
.card { background: #1a1a26; border: 1px solid #2a2a3a; border-radius: 7px; padding: 12px; }
.card h2 { font-size: 10px; color: #555; margin-bottom: 10px; letter-spacing: 1px; }
/* mode badge */
.mode-bar { display: flex; align-items: center; gap: 10px; }
.badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;
         letter-spacing: 1px; }
.badge.teleop { background: #0d2d40; color: #7ec8e3; border: 1px solid #2a5a7a; }
.badge.auto   { background: #0d3020; color: #4aaa77; border: 1px solid #1a5a3a; }
.badge.loading{ background: #2d2a10; color: #aaa055; border: 1px solid #5a5010; }
/* keyboard */
.keys { display: grid; grid-template-columns: repeat(5, 36px); gap: 4px; }
kbd { display: inline-flex; align-items: center; justify-content: center;
      width: 36px; height: 36px; background: #252535; border: 1px solid #3a3a4a;
      border-radius: 5px; font-size: 12px; color: #bbb; transition: all .08s; }
kbd.active { background: #2a5a8a; border-color: #7ec8e3; color: #fff; transform: scale(.93); }
kbd.blank  { visibility: hidden; }
kbd.grp    { background: #252535; border-color: #3a3a4a; color: #bbb; }
kbd.grp.active { background: #8a2a2a; border-color: #e37e7e; color: #fff; }
.key-hint { font-size: 11px; color: #666; margin-top: 6px; line-height: 1.9; }
/* action display */
.axes { display: flex; gap: 6px; flex-wrap: wrap; }
.ax { background: #0f0f18; border: 1px solid #2a2a3a; border-radius: 5px;
      padding: 5px 8px; min-width: 70px; text-align: center; }
.ax span { display: block; font-size: 9px; color: #555; }
.ax .v { color: #7ec8e3; font-size: 13px; font-weight: bold; }
/* model panel */
.form-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.form-row label { font-size: 11px; color: #777; min-width: 90px; flex-shrink: 0; }
.form-row select, .form-row input[type=text] {
  flex: 1; background: #0f0f18; border: 1px solid #2a2a3a; color: #ccc;
  border-radius: 5px; padding: 5px 8px; font-size: 12px; font-family: monospace; }
.form-row input[type=range] { flex: 1; accent-color: #7ec8e3; }
.form-row .range-val { min-width: 24px; text-align: right; color: #7ec8e3; }
.btn { padding: 7px 18px; border-radius: 6px; border: none; cursor: pointer;
       font-size: 12px; font-weight: bold; letter-spacing: 1px; transition: all .1s; }
.btn-start { background: #1a4a2a; color: #4aaa77; border: 1px solid #2a7a3a; }
.btn-start:hover { background: #2a6a3a; }
.btn-stop  { background: #4a1a1a; color: #e07070; border: 1px solid #7a2a2a; }
.btn-stop:hover  { background: #6a2a2a; }
.btn:disabled { opacity: .4; cursor: not-allowed; }
.log { background: #080810; border: 1px solid #1a1a2a; border-radius: 5px;
       padding: 8px; font-size: 11px; color: #777; font-family: monospace;
       max-height: 80px; overflow-y: auto; }
.log .ok  { color: #4aaa77; }
.log .err { color: #e07070; }
.log .info{ color: #7ec8e3; }
/* sliders */
.slider-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.slider-row label { font-size: 11px; color: #777; min-width: 90px; }
.slider-row input[type=range] { flex: 1; accent-color: #7ec8e3; }
.slider-row .sv { min-width: 32px; color: #7ec8e3; text-align: right; }
</style>
</head>
<body>
<h1>LIBERO TELEOP</h1>
<div class="layout">
  <!-- cameras -->
  <div class="cameras">
    <div class="cam-box"><label>AGENT VIEW</label>
      <img id="cam_main" src="/video" width="256" height="256"></div>
    <div class="cam-box"><label>WRIST CAM</label>
      <img id="cam_wrist" src="/wrist" width="256" height="256"></div>
  </div>

  <!-- right panel -->
  <div class="panel">

    <!-- mode -->
    <div class="card">
      <h2>РЕЖИМ</h2>
      <div class="mode-bar">
        <span class="badge teleop" id="mode_badge">TELEOP</span>
        <span id="mode_text" style="color:#777;font-size:11px">Ручное управление</span>
      </div>
    </div>

    <!-- keyboard -->
    <div class="card">
      <h2>КЛАВИАТУРА</h2>
      <div class="keys">
        <kbd class="blank"></kbd><kbd id="k_q">Q</kbd><kbd id="k_w">W</kbd>
        <kbd id="k_e">E</kbd><kbd class="blank"></kbd>
        <kbd class="blank"></kbd><kbd id="k_a">A</kbd><kbd id="k_s">S</kbd>
        <kbd id="k_d">D</kbd><kbd class="blank"></kbd>
        <kbd id="k_ArrowLeft">←</kbd><kbd id="k_ArrowUp">↑</kbd>
        <kbd id="k_ArrowDown">↓</kbd><kbd id="k_ArrowRight">→</kbd>
        <kbd class="blank"></kbd><kbd class="blank"></kbd>
        <kbd class="blank"></kbd><kbd class="grp" id="k_spc">SPC</kbd>
        <kbd class="blank"></kbd><kbd class="blank"></kbd>
      </div>
      <div class="key-hint">
        W/S — Y &nbsp; A/D — X &nbsp; Q/E — Z &nbsp; ←/→ — Yaw &nbsp; ↑/↓ — Pitch<br>
        <b>SPACE (удерж.)</b> — захват закрыт &nbsp; <b>отпустить</b> — открыт
      </div>
      <div style="margin-top:10px">
        <button class="btn" id="btn_reset" onclick="resetSim()"
          style="background:#1a2a40;color:#7ec8e3;border:1px solid #2a5a7a;">
          ↺ СБРОСИТЬ ПОЗИЦИЮ
        </button>
      </div>
    </div>

    <!-- action display -->
    <div class="card">
      <h2>ДЕЙСТВИЕ</h2>
      <div class="axes">
        <div class="ax"><span>X</span><div class="v" id="v_x">0.000</div></div>
        <div class="ax"><span>Y</span><div class="v" id="v_y">0.000</div></div>
        <div class="ax"><span>Z</span><div class="v" id="v_z">0.000</div></div>
        <div class="ax"><span>Roll</span><div class="v" id="v_ro">0.000</div></div>
        <div class="ax"><span>Pitch</span><div class="v" id="v_pi">0.000</div></div>
        <div class="ax"><span>Yaw</span><div class="v" id="v_ya">0.000</div></div>
        <div class="ax"><span>Grip</span><div class="v" id="v_gr">OPEN</div></div>
      </div>
      <div class="slider-row" style="margin-top:10px">
        <label>Шаг движения</label>
        <input type="range" id="step" min="0.01" max="0.5" step="0.01" value="0.08">
        <span class="sv" id="step_v">0.08</span>
      </div>
      <div class="slider-row">
        <label>Шаг поворота</label>
        <input type="range" id="rot_step" min="0.01" max="0.5" step="0.01" value="0.08">
        <span class="sv" id="rot_step_v">0.08</span>
      </div>
    </div>

    <!-- scene info -->
    <div class="card" id="scene_card">
      <h2>ТЕКУЩАЯ СЦЕНА</h2>
      <div id="scene_info" style="font-size:11px;color:#777;">Загрузка…</div>
    </div>

    <!-- model runner -->
    <div class="card">
      <h2>ЗАПУСК МОДЕЛИ</h2>

      <div class="form-row">
        <label>Чекпоинт</label>
        <select id="ckpt_sel" style="flex:1"></select>
      </div>
      <div class="form-row">
        <label>или HF ID</label>
        <input type="text" id="ckpt_hf" placeholder="HuggingFaceVLA/smolvla_libero">
      </div>
      <div class="form-row">
        <label>VLM модель</label>
        <input type="text" id="vlm_model" value="HuggingFaceTB/SmolVLM2-500M-Video-Instruct">
      </div>
      <div class="form-row">
        <label>Задача</label>
        <select id="task_sel" style="flex:1"></select>
      </div>
      <div class="form-row">
        <label>или текст</label>
        <input type="text" id="task_custom"
               placeholder="pick up the ... and place it in the basket">
      </div>
      <div class="form-row">
        <label>n_action_steps</label>
        <input type="range" id="n_steps" min="1" max="50" step="1" value="10">
        <span class="range-val" id="n_steps_v">10</span>
      </div>
      <div class="form-row">
        <label>Точность</label>
        <select id="precision">
          <option value="bf16" selected>BF16</option>
          <option value="int8">INT8</option>
        </select>
      </div>
      <div style="display:flex;gap:8px;margin-top:4px">
        <button class="btn btn-start" id="btn_start" onclick="startPolicy()">▶ ЗАПУСТИТЬ</button>
        <button class="btn btn-stop"  id="btn_stop"  onclick="stopPolicy()" disabled>■ СТОП</button>
      </div>
      <div class="log" id="policy_log" style="margin-top:8px">
        <span class="info">Выберите модель и нажмите ЗАПУСТИТЬ</span>
      </div>
    </div>

  </div>
</div>
<script>
// ── teleop ──────────────────────────────────────────────────────────────────
const pressed = new Set();
let gripClosed = false;
let intervalId = null;
let autoMode = false;

const keyMap = {
  'w':[0,1,0,0,0,0], 's':[0,-1,0,0,0,0],
  'a':[-1,0,0,0,0,0],'d':[1,0,0,0,0,0],
  'q':[0,0,1,0,0,0], 'e':[0,0,-1,0,0,0],
  'ArrowLeft':[0,0,0,0,0,-1], 'ArrowRight':[0,0,0,0,0,1],
  'ArrowUp':[0,0,0,0,1,0],    'ArrowDown':[0,0,0,0,-1,0],
};

document.getElementById('step').addEventListener('input', e =>
  document.getElementById('step_v').textContent = e.target.value);
document.getElementById('rot_step').addEventListener('input', e =>
  document.getElementById('rot_step_v').textContent = e.target.value);
document.getElementById('n_steps').addEventListener('input', e =>
  document.getElementById('n_steps_v').textContent = e.target.value);

function buildAction() {
  const step = parseFloat(document.getElementById('step').value);
  const rStep = parseFloat(document.getElementById('rot_step').value);
  const acc = [0,0,0,0,0,0];
  for (const k of pressed) {
    const d = keyMap[k]; if (!d) continue;
    for (let i = 0; i < 6; i++) acc[i] += d[i] * (i < 3 ? step : rStep);
  }
  return [...acc, gripClosed ? -1.0 : 1.0];
}

function clamp(v,lo,hi){return Math.max(lo,Math.min(hi,v));}
function isActive(){return pressed.size > 0 || gripClosed;}

function sendAction() {
  if (!isActive() || autoMode) return;
  const a = buildAction().map((v,i)=> i<6?clamp(v,-1,1):v);
  fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({action:a})}).catch(()=>{});
  ['v_x','v_y','v_z','v_ro','v_pi','v_ya'].forEach((id,i)=>
    document.getElementById(id).textContent = a[i].toFixed(3));
  document.getElementById('v_gr').textContent = gripClosed ? 'CLOSE' : 'OPEN';
}

function startInterval(){if(!intervalId) intervalId=setInterval(sendAction,80);}
function maybeStop(){
  if(!isActive()){
    clearInterval(intervalId); intervalId=null;
    ['v_x','v_y','v_z','v_ro','v_pi','v_ya'].forEach(id=>
      document.getElementById(id).textContent='0.000');
  }
}

async function resetSim() {
  const btn = document.getElementById('btn_reset');
  btn.disabled = true;
  btn.textContent = '↺ Сброс…';
  try {
    await fetch('/reset', {method:'POST'});
  } catch(e) {}
  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = '↺ СБРОСИТЬ ПОЗИЦИЮ';
  }, 1500);
}

document.addEventListener('keydown', e => {
  if (autoMode) return;
  if (e.repeat) return;
  if (e.key === ' ') {
    e.preventDefault();
    if (gripClosed) return;
    gripClosed = true;
    document.getElementById('k_spc').classList.add('active');
    document.getElementById('v_gr').textContent = 'CLOSE';
    startInterval(); return;
  }
  const k = keyMap[e.key] ? e.key : e.key.toLowerCase();
  if (!keyMap[k]) return;
  e.preventDefault();
  pressed.add(k);
  const el = document.getElementById('k_'+k);
  if (el) el.classList.add('active');
  startInterval();
});

document.addEventListener('keyup', e => {
  if (e.key === ' ') {
    gripClosed = false;
    document.getElementById('k_spc').classList.remove('active');
    document.getElementById('v_gr').textContent = 'OPEN';
    const a = buildAction();
    if (!autoMode) fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:a})}).catch(()=>{});
    maybeStop(); return;
  }
  const k = keyMap[e.key] ? e.key : e.key.toLowerCase();
  pressed.delete(k);
  const el = document.getElementById('k_'+k);
  if (el) el.classList.remove('active');
  maybeStop();
});

window.addEventListener('keydown', e => {
  if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '].includes(e.key)) e.preventDefault();
});

// ── model runner ─────────────────────────────────────────────────────────────
async function loadModels() {
  try {
    const r = await fetch('/models');
    const data = await r.json();
    const sel = document.getElementById('ckpt_sel');
    sel.innerHTML = '<option value="">— выбрать локальный —</option>';
    data.models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.path; opt.textContent = m.name;
      sel.appendChild(opt);
    });
    document.getElementById('vlm_model').value = data.vlm_default;
  } catch(e) { console.warn('models load failed', e); }

  const tsel = document.getElementById('task_sel');
  const tasks = LIBERO_TASKS;
  tsel.innerHTML = '<option value="">— выбрать задачу —</option>';
  tasks.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t; opt.textContent = t;
    tsel.appendChild(opt);
  });
}

const LIBERO_TASKS = [
  "pick up the alphabet soup and place it in the basket",
  "pick up the cream cheese and place it in the basket",
  "pick up the salad dressing and place it in the basket",
  "pick up the bbq sauce and place it in the basket",
  "pick up the ketchup and place it in the basket",
  "pick up the milk and place it in the basket",
  "pick up the orange juice and place it in the basket",
  "pick up the tomato sauce and place it in the basket",
  "pick up the butter and place it in the basket",
  "pick up the chocolate pudding and place it in the basket",
];

function getCheckpoint() {
  const hf = document.getElementById('ckpt_hf').value.trim();
  if (hf) return hf;
  return document.getElementById('ckpt_sel').value || null;
}

function getTask() {
  const custom = document.getElementById('task_custom').value.trim();
  if (custom) return custom;
  return document.getElementById('task_sel').value || null;
}

function logLine(text, cls='info') {
  const el = document.getElementById('policy_log');
  el.innerHTML += `<div class="${cls}">${text}</div>`;
  el.scrollTop = el.scrollHeight;
}

function setMode(mode, label) {
  autoMode = (mode !== 'teleop');
  const badge = document.getElementById('mode_badge');
  const text  = document.getElementById('mode_text');
  badge.className = 'badge ' + mode;
  badge.textContent = mode === 'auto' ? 'AUTO' : (mode === 'loading' ? 'LOADING' : 'TELEOP');
  text.textContent = label;
  document.getElementById('btn_start').disabled = autoMode;
  document.getElementById('btn_stop').disabled  = !autoMode;
}

async function startPolicy() {
  const ckpt = getCheckpoint();
  const task = getTask();
  if (!ckpt) { logLine('Выберите чекпоинт!', 'err'); return; }
  if (!task) { logLine('Введите задачу!',    'err'); return; }
  const vlm   = document.getElementById('vlm_model').value.trim()
             || 'HuggingFaceTB/SmolVLM2-500M-Video-Instruct';
  const steps = document.getElementById('n_steps').value;
  const prec  = document.getElementById('precision').value;

  document.getElementById('policy_log').innerHTML = '';
  logLine(`Загружаю модель: ${ckpt}`, 'info');
  setMode('loading', 'Загрузка модели…');

  try {
    const r = await fetch('/policy/start', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        checkpoint:ckpt, vlm_model:vlm, task,
        n_action_steps:parseInt(steps), precision:prec,
      }),
    });
    const d = await r.json();
    if (d.ok) {
      seenEpisodes = 0;
      setMode('loading', 'Загрузка модели…');
      logLine('Процесс модели запущен', 'ok');
      logLine(`Задача: ${task}`, 'info');
      pollStatus();
    } else {
      setMode('teleop', 'Ручное управление');
      logLine('Ошибка: ' + (d.error || 'неизвестно'), 'err');
    }
  } catch(e) {
    setMode('teleop', 'Ручное управление');
    logLine('Ошибка запроса: '+e, 'err');
  }
}

async function stopPolicy() {
  try {
    await fetch('/policy/stop', {method:'POST'});
  } catch(e) {}
  setMode('teleop', 'Ручное управление');
  logLine('Политика остановлена', 'info');
}

let pollTimer = null;
let seenEpisodes = 0;
async function pollStatus() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const r = await fetch('/policy/status');
      const d = await r.json();
      if (d.status === 'running') {
        document.getElementById('mode_text').textContent =
          `Модель: ${d.checkpoint.split('/').pop()} | ` +
          `Действия: ${d.actions} | SR: ${d.successes}/${d.episodes}`;
        if (!autoMode) { setMode('auto', `Модель: ${d.checkpoint.split('/').pop()}`); }
      } else if (d.status === 'loading') {
        document.getElementById('mode_text').textContent = 'Загрузка модели…';
        document.getElementById('btn_start').disabled = true;
      } else if (d.status === 'stopped') {
        clearInterval(pollTimer);
        if (autoMode) {
          setMode('teleop', 'Ручное управление');
          logLine('Модель остановлена', 'info');
        }
      }
      if (d.episodes > seenEpisodes) {
        seenEpisodes = d.episodes;
        const cls = d.last_result && d.last_result.success ? 'ok' : 'err';
        const outcome = d.last_result.success ? 'SUCCESS' : 'FAIL';
        logLine(
          `Эпизод ${d.episodes}: ${outcome} (${d.last_result.actions} действий)`, cls
        );
      }
    } catch(e) {}
  }, 1000);
}

async function loadScene() {
  try {
    const r = await fetch('/scene');
    const d = await r.json();
    const el = document.getElementById('scene_info');
    el.innerHTML =
      `<span style="color:#7ec8e3">task_id=${d.task_id}</span> &nbsp;|&nbsp; ` +
      `На столе: <span style="color:#4aaa77">${d.objects.join(', ')}</span>`;
    const tsel = document.getElementById('task_sel');
    tsel.value = d.task;
    for (const opt of tsel.options) opt.disabled = !!opt.value && opt.value !== d.task;
    const custom = document.getElementById('task_custom');
    custom.value = '';
    custom.disabled = true;
    custom.placeholder = 'Инструкция связана с текущей сценой';
  } catch(e) { console.warn('scene load failed', e); }
}

async function initialize() {
  await loadModels();
  await loadScene();
}
initialize();
</script>
</body>
</html>"""
# fmt: on


# ──────────────────────────────────────────────────────────────────────────────
# Policy process manager
# ──────────────────────────────────────────────────────────────────────────────
class PolicyProcess:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._actions = 0
        self._checkpoint = ""
        self._ready = False

    @property
    def actions(self) -> int:
        with self._lock:
            return self._actions

    @property
    def active(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def increment(self) -> None:
        with self._lock:
            self._actions += 1

    def start(self, checkpoint: str, vlm_model: str, task: str,
              n_action_steps: int, precision: str) -> None:
        self.stop()
        self._checkpoint = checkpoint
        self._actions = 0
        self._ready = False
        env = {**os.environ,
               "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID", "73")}
        cmd = [
            "ros2", "run", "vla_bridge", "smolvla_node",
            "--ros-args",
            "-p", f"checkpoint:={checkpoint}",
            "-p", f"vlm_model:={vlm_model}",
            "-p", f"task:={task}",
            "-p", f"n_action_steps:={n_action_steps}",
            "-p", f"precision:={precision}",
            "-p", "device:=cuda",
            "-p", "inference_hz:=10.0",
        ]
        with self._lock:
            self._proc = subprocess.Popen(
                cmd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
                preexec_fn=os.setsid,
            )
        # monitor stdout in background thread
        threading.Thread(target=self._monitor, daemon=True).start()

    def _monitor(self) -> None:
        proc = self._proc
        if proc is None:
            return
        for line in proc.stdout:
            print(f"[smolvla] {line}", end="", flush=True)
            if "smolvla_ready" in line.lower():
                with self._lock:
                    self._ready = True
        proc.wait()
        with self._lock:
            self._ready = False
        print(f"[smolvla] process exited with code {proc.returncode}", flush=True)

    def stop(self) -> None:
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()

    def status(self) -> dict:
        with self._lock:
            alive = self._proc is not None and self._proc.poll() is None
            ready = self._ready
            actions = self._actions
        if alive and not ready:
            status = "loading"
        elif alive:
            status = "running"
        else:
            status = "stopped"
        return {"status": status, "checkpoint": self._checkpoint, "actions": actions}


# ──────────────────────────────────────────────────────────────────────────────
# ROS2 node
# ──────────────────────────────────────────────────────────────────────────────
class WebTeleopNode(Node):
    def __init__(self):
        super().__init__("web_teleop")
        self._frame_main: bytes | None = None
        self._frame_wrist: bytes | None = None
        self._lock = threading.Lock()
        self._port = int(self.declare_parameter("port", 8888).value)
        self._suite = self.declare_parameter("suite", "libero_object").value
        self._task_id = int(self.declare_parameter("task_id", 0).value)
        self._data_dir = Path(os.environ.get("ROBOTICS_DATA_DIR", "/data"))
        self._policy = PolicyProcess()
        self._scene_cache: dict | None = None
        self._episodes = 0
        self._successes = 0
        self._last_result: dict | None = None

        self.create_subscription(Image, "/camera/image_raw", self._on_main, 1)
        self.create_subscription(Image, "/camera/wrist/image_raw", self._on_wrist, 1)
        self.create_subscription(Float32MultiArray, "/vla/action", self._on_policy_action, 1)
        self.create_subscription(String, "/sim/episode_result", self._on_episode_result, 1)
        self._pub = self.create_publisher(Float32MultiArray, "/vla/action", 1)
        self._reset_pub = self.create_publisher(Bool, "/sim/reset", 1)

        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._serve, daemon=True).start()
        self.get_logger().info(f"Teleop UI → http://localhost:{self._port}")

    # ── camera helpers ───────────────────────────────────────────────────────
    def _to_jpeg(self, msg: Image) -> bytes:
        arr = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        arr = cv2.flip(arr, 0)
        _, buf = cv2.imencode(".jpg", cv2.cvtColor(arr, cv2.COLOR_RGB2BGR),
                              [cv2.IMWRITE_JPEG_QUALITY, 80])
        return bytes(buf)

    def _on_main(self, msg: Image) -> None:
        with self._lock:
            self._frame_main = self._to_jpeg(msg)

    def _on_wrist(self, msg: Image) -> None:
        with self._lock:
            self._frame_wrist = self._to_jpeg(msg)

    def _on_policy_action(self, _msg: Float32MultiArray) -> None:
        if self._policy.active:
            self._policy.increment()

    def _on_episode_result(self, msg: String) -> None:
        try:
            result = json.loads(msg.data)
        except (TypeError, ValueError):
            self.get_logger().warning("Ignoring malformed episode result")
            return
        with self._lock:
            self._episodes += 1
            self._successes += int(bool(result.get("success", False)))
            self._last_result = result

    # ── aiohttp server ───────────────────────────────────────────────────────
    def _serve(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run_app())

    async def _run_app(self) -> None:
        app = web.Application()
        app.router.add_get("/",              self._index)
        app.router.add_get("/video",         lambda r: self._stream(r, "main"))
        app.router.add_get("/wrist",         lambda r: self._stream(r, "wrist"))
        app.router.add_post("/action",       self._action)
        app.router.add_post("/reset",        self._reset)
        app.router.add_get("/models",        self._list_models)
        app.router.add_post("/policy/start", self._policy_start)
        app.router.add_post("/policy/stop",  self._policy_stop)
        app.router.add_get("/policy/status", self._policy_status)
        app.router.add_get("/scene",         self._scene_info)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", self._port).start()
        while True:
            await asyncio.sleep(3600)

    async def _index(self, _: web.Request) -> web.Response:
        return web.Response(text=HTML, content_type="text/html")

    async def _stream(self, request: web.Request, cam: str) -> web.StreamResponse:
        resp = web.StreamResponse(
            headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"}
        )
        await resp.prepare(request)
        try:
            while True:
                with self._lock:
                    frame = self._frame_main if cam == "main" else self._frame_wrist
                if frame:
                    await resp.write(
                        b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                    )
                await asyncio.sleep(0.08)
        except Exception:
            pass
        return resp

    async def _action(self, request: web.Request) -> web.Response:
        if self._policy.active:
            return web.json_response(
                {"ok": False, "error": "manual control is disabled while policy runs"},
                status=409,
            )
        data = await request.json()
        action = [float(x) for x in data.get("action", [0.0] * 7)]
        if len(action) == 7 and all(np.isfinite(action)):
            self._pub.publish(Float32MultiArray(data=action))
        return web.json_response({"ok": True})

    async def _reset(self, _: web.Request) -> web.Response:
        self._reset_pub.publish(Bool(data=True))
        self.get_logger().info("Reset command sent to sim")
        return web.json_response({"ok": True})

    # ── model discovery ──────────────────────────────────────────────────────
    async def _list_models(self, _: web.Request) -> web.Response:
        models = []
        models_dir = self._data_dir / "models"
        if models_dir.exists():
            for d in sorted(models_dir.iterdir()):
                if d.is_dir() and (d / "config.json").exists():
                    models.append({"name": d.name, "path": str(d)})
        local_vlm = models_dir / "vlm"
        vlm_default = (
            str(local_vlm)
            if (local_vlm / "config.json").exists()
            else "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
        )
        return web.json_response({"models": models, "vlm_default": vlm_default})

    # ── policy control ───────────────────────────────────────────────────────
    async def _policy_start(self, request: web.Request) -> web.Response:
        data = await request.json()
        checkpoint   = data.get("checkpoint", "")
        vlm_model    = data.get("vlm_model", "HuggingFaceTB/SmolVLM2-500M-Video-Instruct")
        task         = data.get("task", "")
        n_steps      = int(data.get("n_action_steps", 10))
        precision    = data.get("precision", "bf16")
        if not checkpoint or not task:
            return web.json_response({"ok": False, "error": "checkpoint and task are required"})
        expected_task = LIBERO_TASKS[self._task_id]
        if task != expected_task:
            return web.json_response(
                {"ok": False, "error": f"current scene requires: {expected_task}"},
                status=400,
            )
        if not 1 <= n_steps <= 50 or precision not in {"bf16", "int8"}:
            return web.json_response(
                {"ok": False, "error": "invalid policy parameters"}, status=400
            )
        try:
            with self._lock:
                self._episodes = 0
                self._successes = 0
                self._last_result = None
            self._reset_pub.publish(Bool(data=True))
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._policy.start(checkpoint, vlm_model, task, n_steps, precision),
            )
            self.get_logger().info(f"Policy started: {checkpoint} / {task}")
            return web.json_response({"ok": True})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)})

    async def _policy_stop(self, _: web.Request) -> web.Response:
        await asyncio.get_event_loop().run_in_executor(None, self._policy.stop)
        self.get_logger().info("Policy stopped by user")
        return web.json_response({"ok": True})

    async def _policy_status(self, _: web.Request) -> web.Response:
        status = self._policy.status()
        with self._lock:
            status.update(
                episodes=self._episodes,
                successes=self._successes,
                last_result=self._last_result,
            )
        return web.json_response(status)

    async def _scene_info(self, _: web.Request) -> web.Response:
        if self._scene_cache is None:
            bddl_root = Path(
                "/opt/venv/lib/python3.12/site-packages/libero/libero/bddl_files"
            )
            bddl_dir = bddl_root / self._suite
            objects = []
            bddl_file = None
            if bddl_dir.exists():
                files = sorted(bddl_dir.glob("*.bddl"))
                if self._task_id < len(files):
                    bddl_file = files[self._task_id]
            if bddl_file and bddl_file.exists():
                text = bddl_file.read_text()
                m = re.search(r'\(:objects(.*?)\)', text, re.DOTALL)
                if m:
                    for line in m.group(1).strip().splitlines():
                        line = line.strip()
                        if ' - ' in line:
                            _, typ = line.split(' - ', 1)
                            typ = typ.strip()
                            if typ not in ('basket', 'floor'):
                                objects.append(typ)
            self._scene_cache = {
                "task_id": self._task_id,
                "suite": self._suite,
                "task": LIBERO_TASKS[self._task_id],
                "objects": objects,
            }
        return web.json_response(self._scene_cache)

    def destroy_node(self) -> None:
        self._policy.stop()
        super().destroy_node()


def main():
    rclpy.init()
    node = WebTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
