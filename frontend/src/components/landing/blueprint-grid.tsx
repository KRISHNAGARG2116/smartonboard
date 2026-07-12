import { useEffect, useRef } from 'react'
import './blueprint-grid.css'

// Preserved from the supplied Blueprint Shader Grid implementation.
const FRAGMENT_SHADER = `#version 300 es
precision highp float;
out vec4 fragColor; in vec2 v_uv;
uniform vec3 iResolution; uniform float iTime; uniform int iFrame; uniform vec4 iMouse;
const float GRID_SCALE=18.0,MAJOR_STEP=4.0,THIN_WIDTH=0.010,MAJOR_WIDTH=0.018,SCROLL_SPEED=0.02;
const float VIGNETTE_AMT=0.28,MESH_AMT=0.85,NOISE_AMT=0.030,DITHER_DARK=0.010,DITHER_LIGHT=0.004;
const float ASCII_AMT=0.23,ASCII_SCALE=26.0,ASCII_EVERY=2.0;
float bayer4(vec2 p){ivec2 ip=ivec2(int(mod(p.x,4.0)),int(mod(p.y,4.0)));int idx=ip.y*4+ip.x;int m[16];m[0]=0;m[1]=8;m[2]=2;m[3]=10;m[4]=12;m[5]=4;m[6]=14;m[7]=6;m[8]=3;m[9]=11;m[10]=1;m[11]=9;m[12]=15;m[13]=7;m[14]=13;m[15]=5;return float(m[idx])/15.0;}
float hash21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);float a=hash21(i),b=hash21(i+vec2(1,0)),c=hash21(i+vec2(0,1)),d=hash21(i+vec2(1,1));vec2 u=f*f*(3.0-2.0*f);return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);}
float gridLineAA(vec2 uv,float scale,float width){vec2 g=abs(fract(uv*scale)-0.5);float d=min(g.x,g.y);float aa=fwidth(d);return 1.0-smoothstep(width,width+aa,d);}float majorGridAA(vec2 uv,float scale,float stepN,float width){return gridLineAA(uv,max(1.0,scale/stepN),width);}
vec3 meshGradient(vec2 uv){vec2 p0=vec2(-.70,-.45),p1=vec2(.75,-.35),p2=vec2(-.65,.65),p3=vec2(.80,.55);vec3 c0=vec3(.05,.10,.26),c1=vec3(.08,.16,.36),c2=vec3(.03,.09,.22),c3=vec3(.10,.20,.40);float e=2.0;float w0=pow(1.0/(.2+distance(uv,p0)),e),w1=pow(1.0/(.2+distance(uv,p1)),e),w2=pow(1.0/(.2+distance(uv,p2)),e),w3=pow(1.0/(.2+distance(uv,p3)),e),ws=w0+w1+w2+w3;return(c0*w0+c1*w1+c2*w2+c3*w3)/ws;}
float sdLineX(vec2 p,float w){return 1.0-smoothstep(w,w+fwidth(p.y),abs(p.y));}float sdLineY(vec2 p,float w){return 1.0-smoothstep(w,w+fwidth(p.x),abs(p.x));}float sdDiag1(vec2 p,float w){float d=abs(p.x+p.y)/sqrt(2.0);return 1.0-smoothstep(w,w+fwidth(d),d);}float sdDiag2(vec2 p,float w){float d=abs(p.x-p.y)/sqrt(2.0);return 1.0-smoothstep(w,w+fwidth(d),d);}float sdDot(vec2 p,float r){float d=length(p);return 1.0-smoothstep(r,r+fwidth(d),d);}
float asciiGlyph(vec2 p,float level){float w=.11,r=.10,g0=sdDot(p,r),g1=sdLineX(p,w),g2=sdLineY(p,w),g3=max(sdLineX(p,w),sdLineY(p,w)),g4=sdDiag1(p,w),g5=sdDiag2(p,w),g6=max(sdDiag1(p,w),sdDiag2(p,w)),g7=max(sdLineX(p,w),max(sdLineY(p,w),g6)),m=0.;m=mix(m,g0,smoothstep(0.,.12,level)*(1.-step(level,.12)));m=mix(m,g1,smoothstep(.12,.28,level)*(1.-step(level,.28)));m=mix(m,g2,smoothstep(.28,.44,level)*(1.-step(level,.44)));m=mix(m,g3,smoothstep(.44,.60,level)*(1.-step(level,.60)));m=mix(m,g4,smoothstep(.60,.72,level)*(1.-step(level,.72)));m=mix(m,g5,smoothstep(.72,.84,level)*(1.-step(level,.84)));m=mix(m,g6,smoothstep(.84,.94,level)*(1.-step(level,.94)));m=mix(m,g7,smoothstep(.94,1.,level));return clamp(m,0.,1.);}
void mainImage(out vec4 outColor,in vec2 fragCoord){vec2 R=iResolution.xy;float t=iTime;vec2 uv=(fragCoord-.5*R)/max(R.y,1.);vec3 bg=mix(vec3(.03,.06,.12),vec3(.05,.09,.18),smoothstep(-.92,.55,-uv.y));bg=mix(bg,meshGradient(uv),MESH_AMT);bg*=clamp(pow(1.-VIGNETTE_AMT*length(uv),1.),0.,1.);vec2 uvAnim=uv+SCROLL_SPEED*t*normalize(vec2(1.,-.55));float thin=gridLineAA(uvAnim,GRID_SCALE,THIN_WIDTH),major=majorGridAA(uvAnim,GRID_SCALE,MAJOR_STEP,MAJOR_WIDTH);vec3 col=bg+vec3(.58,.66,.95)*thin*.25+vec3(.78,.84,1.)*major*.52;vec2 idx=floor(uvAnim*(GRID_SCALE/MAJOR_STEP)+.5);float selX=1.-step(.001,abs(fract(idx.x/ASCII_EVERY))),selY=1.-step(.001,abs(fract(idx.y/ASCII_EVERY)));if(ASCII_AMT>.001){vec2 cellF=fract(uv*ASCII_SCALE)-.5;float lvl=clamp(dot(col,vec3(.2126,.7152,.0722)),0.,1.);float glyph=asciiGlyph(cellF,lvl);float asciiMask=max(selX,selY)*major;vec3 asciiColor=mix(vec3(.50,.70,1.),meshGradient(uv),.25);col=mix(col,col+asciiColor*glyph*.30,ASCII_AMT*asciiMask);}col+=(vnoise(fragCoord*.6+vec2(t*12.,-t*9.))-.5)*NOISE_AMT;float luma=dot(col,vec3(.2126,.7152,.0722));col+=(bayer4(fragCoord)-.5)*mix(DITHER_DARK,DITHER_LIGHT,luma);outColor=vec4(tanh(col),1.);}void main(){mainImage(fragColor,gl_FragCoord.xy);}`

const VERTEX_SHADER = `#version 300 es
precision highp float;layout(location=0)in vec2 a_pos;out vec2 v_uv;void main(){v_uv=a_pos*.5+.5;gl_Position=vec4(a_pos,0.,1.);}`

export function BlueprintGrid({ className = '' }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const gl = canvas.getContext('webgl2', { premultipliedAlpha: false })
    if (!gl) return
    const compile = (type: number, source: string) => { const shader = gl.createShader(type)!; gl.shaderSource(shader, source); gl.compileShader(shader); return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null }
    const vertex = compile(gl.VERTEX_SHADER, VERTEX_SHADER), fragment = compile(gl.FRAGMENT_SHADER, FRAGMENT_SHADER)
    if (!vertex || !fragment) return
    const program = gl.createProgram()!; gl.attachShader(program, vertex); gl.attachShader(program, fragment); gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return
    const vao = gl.createVertexArray()!, buffer = gl.createBuffer()!, resolution = gl.getUniformLocation(program, 'iResolution'), time = gl.getUniformLocation(program, 'iTime'), frame = gl.getUniformLocation(program, 'iFrame')
    gl.bindVertexArray(vao); gl.bindBuffer(gl.ARRAY_BUFFER, buffer); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW); gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    let raf = 0; let frames = 0; const started = performance.now()
    const resize = () => { const dpr = Math.min(window.devicePixelRatio || 1, 2); const width = Math.max(1, Math.floor(canvas.clientWidth * dpr)); const height = Math.max(1, Math.floor(canvas.clientHeight * dpr)); if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; gl.viewport(0, 0, width, height) } }
    const observer = new ResizeObserver(resize); observer.observe(canvas); resize()
    const draw = (now: number) => { frames += 1; gl.useProgram(program); gl.uniform3f(resolution, canvas.width, canvas.height, Math.min(window.devicePixelRatio || 1, 2)); gl.uniform1f(time, (now - started) / 1000); gl.uniform1i(frame, frames); gl.drawArrays(gl.TRIANGLES, 0, 3); raf = requestAnimationFrame(draw) }
    raf = requestAnimationFrame(draw)
    return () => { cancelAnimationFrame(raf); observer.disconnect(); gl.deleteBuffer(buffer); gl.deleteVertexArray(vao); gl.deleteProgram(program); gl.deleteShader(vertex); gl.deleteShader(fragment) }
  }, [])

  return <div className={`blueprint-shader ${className}`} aria-hidden="true"><canvas ref={canvasRef} /></div>
}
