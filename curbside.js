const scene=new THREE.Scene(), sky=0xd9e8e4;scene.background=new THREE.Color(sky);
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);renderer.xr.enabled=true;document.body.appendChild(renderer.domElement);
const cam=new THREE.PerspectiveCamera(36,innerWidth/innerHeight,.1,180);
scene.add(new THREE.HemisphereLight(0xfff9e1,0xa4b8bd,2.35));
const sun=new THREE.DirectionalLight(0xffe2b8,2.15);sun.position.set(-6,12,7);scene.add(sun);
const world=new THREE.Group();scene.add(world);
const geo=new THREE.BoxGeometry(),mat={};
function solid(shape,x,y,z,col,parent=world){const m=new THREE.Mesh(shape,mat[col]??=new THREE.MeshStandardMaterial({color:col,roughness:.85,flatShading:true}));m.position.set(x,y,z);parent.add(m);return m}
function box(x,y,z,w,h,d,col,p){let m=solid(geo,x,y,z,col,p);m.scale.set(w,h,d);return m}
function cyl(x,y,z,r,h,col,n=12,p){return solid(new THREE.CylinderGeometry(r,r,h,n),x,y,z,col,p)}
function tree(x,z){box(x,1,z,.28,2,.28,0x816449);for(const [dx,y,r,c] of [[0,2.4,1,0x36866b],[-.45,2.95,.82,0x56a577],[.35,3.12,.75,0x76b17c]])solid(new THREE.IcosahedronGeometry(r,0),x+dx,y,z,c)}
box(0,-.62,0,23,1.18,13,0x334f50);box(0,-.06,0,23,.24,13,0xb5b7a7);box(0,.08,1.25,23,.07,3.5,0x506069);
for(let x=-10;x<11;x+=2)box(x,.125,1.25,1,.02,.085,0xf9d787);
for(let x=-11;x<=11;x+=1.2)box(x,.19,-.93,1.16,.2,.83,0xe9ddc5);
for(let x=-11;x<=11;x+=1.2)box(x,.19,3.36,1.16,.2,.66,0xe9ddc5);
for(const [x,w,h,color] of [[-8.7,3.6,3.8,0xba715b],[-4.6,3.7,3.05,0xf1d29b],[-.25,4.25,4.45,0x699698],[4.35,3.95,3.2,0xd49678],[8.65,3.55,4,0xc1b7a1]]){
 box(x,h/2,-3.75,w,h,3.05,color);box(x,h+.12,-3.75,w+.22,.27,3.24,0x485e61);box(x+.5,h+.39,-3.8,.72,.32,.7,0xa7b0a3);
 for(let yy=.96;yy<h-.1;yy+=1.22)for(let k=-1;k<=1;k++){box(x+k*.99,yy,-2.19,.61,.68,.13,0x294957);box(x+k*.99,yy-.31,-2.09,.72,.09,.15,0xf1dec0)}
 box(x,.72,-2.06,.68,1.38,.16,0x3c635f);box(x,1.56,-1.91,1.12,.16,.66,0xf1c079);
}
tree(-10.3,-1.5);tree(2.5,-1.55);tree(9.9,-1.5);tree(-9.4,4.65);tree(9.35,4.8);
for(let x of [-6.7,6.6]){cyl(x,1.25,-.8,.07,2.5,0x3a565a);box(x,2.55,-.56,.12,.1,.55,0x3a565a);box(x,2.52,-.25,.37,.15,.28,0xffe6a5)}
// Furniture left beside the curb, shown at street scale.
const pile=new THREE.Group();pile.position.set(-3.6,.16,3.95);pile.rotation.y=.23;world.add(pile);
box(0,.36,0,2.2,.45,.92,0xb04e35,pile);box(0,.78,-.42,2.15,.68,.26,0xc36349,pile);
for(const x of [-.52,.52])box(x,.62,.09,.94,.2,.68,0xe18a68,pile);
for(const x of [-1.07,1.07])box(x,.62,0,.24,.52,.98,0xc76749,pile);
const mattress=box(-1.85,.88,-.35,.32,1.77,1.06,0xf1d9ae,pile);mattress.rotation.z=-.34;
for(let j=0;j<3;j++)for(let k=0;k<2;k++)box(-1.62-j*.15,.45+j*.48,-.6+k*.49,.12,.065,.065,0xbda780,pile);
for(let j=0;j<2;j++)cyl(1.68,.15+j*.22,0,.42,.22,0x283539,16,pile);
for(const [x,z] of [[2.3,.32],[2.12,-.46]]){solid(new THREE.IcosahedronGeometry(.38,0),x,.32,z,0x34494c,pile);box(x,.63,z,.13,.12,.11,0x34494c,pile)}
function tag(str,x,y,z,size){const cvs=document.createElement('canvas');cvs.width=512;cvs.height=96;const c=cvs.getContext('2d');c.fillStyle='#143936';c.fillRect(0,0,512,96);c.font='bold '+(str.length<=4?78:57)+'px Arial';c.fillStyle='#fff5de';c.textAlign='center';c.fillText(str,256,66);const tex=new THREE.CanvasTexture(cvs);tex.colorSpace=THREE.SRGBColorSpace;const o=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,depthTest:false}));o.position.set(x,y,z);o.scale.set(size,size*96/512,1);world.add(o);return o}
const label=tag('DUMPING REPORT',-3.6,2.12,4,3.25);
const bars=[], vals=[115,169,116,121,123,227], titles=['JUL 1','JUL 8','JUL 15','JUL 22','FORECAST','ACTUAL'];
for(let j=0;j<6;j++){let x=-.9+j*1.45,z=4.65;bars.push([box(x,.25,z,.84,1,.84,j<4?0x339887:j==4?0x188caa:0xe67438),tag(titles[j],x,1,z,j<4?1.12:1.5),tag(String(vals[j]),x,1,z,1)])}
const ring=solid(new THREE.RingGeometry(.7,.79,48),-3.6,.32,3.95,0xf5af45);ring.rotation.x=-Math.PI/2;
const headings=['A sofa at the curb','Four weeks of reports','What would Monday predict?','227 reports by Sunday'];
const caps=['Illegal dumping • An illustrative District 3 street','July 2024 • 115, 169, 116 and 121 reports','Poisson forecast • About 123 new reports','227 reported • About 104 above forecast'];
const stages=[0,10,20,30],smooth=a=>Math.max(0,Math.min(1,a))**2*(3-2*Math.max(0,Math.min(1,a)));
let offset=0,paused=false,start=performance.now(),record=new URLSearchParams(location.search).has('record');
function draw(t){let stage=t<10?0:t<20?1:t<30?2:3;heading.textContent=headings[stage];caption.textContent=caps[stage];label.visible=stage===0;ring.visible=stage===0;ring.scale.setScalar(1.2+.22*Math.sin(t*3));
 bars.forEach(([m,l,num],j)=>{let v=smooth((t-(j<4?10+j*.55:j===4?20:30))/1.1),h=vals[j]*.018*v;m.visible=l.visible=num.visible=v>.02;m.scale.y=Math.max(.001,h);m.position.y=.2+h/2;l.position.y=.49+h;num.position.y=.84+h});
 let a=smooth(t/10),b=smooth((t-10)/10);const focus=new THREE.Vector3(-3.6+5.7*a,.85+.55*a,3.9-.6*a);
 if(!renderer.xr.isPresenting){const angle=.43*Math.sin(.12*t)-.34;const r=8.5+5*a+2*b;cam.position.set(focus.x+Math.sin(angle)*r,focus.y+3.2+4*a,focus.z+Math.cos(angle)*r);cam.lookAt(focus)}renderer.render(scene,cam)}
window.draw=draw; draw(0);
if(record)document.querySelector('nav').style.display='none';
renderer.setAnimationLoop(()=>{if(!record)draw((offset+(paused?0:(performance.now()-start)/1000))%42)});
pause.onclick=()=>{if(!paused)offset+=(performance.now()-start)/1000;start=performance.now();paused=!paused;pause.textContent=paused?'Play':'Pause'};restart.onclick=()=>{offset=0;start=performance.now();paused=false;pause.textContent='Pause'};
if(navigator.xr)navigator.xr.isSessionSupported('immersive-vr').then(ok=>{xr.hidden=!ok});xr.onclick=async()=>{const session=await navigator.xr.requestSession('immersive-vr');world.scale.setScalar(.48);world.position.set(0,-.4,-6);cam.position.set(0,0,0);cam.rotation.set(0,0,0);await renderer.xr.setSession(session);session.addEventListener('end',()=>{world.scale.setScalar(1);world.position.set(0,0,0)})};
onresize=()=>{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)};
// Render the miniature using a measured marker pose for the recorded tabletop AR shot.
window.drawMarker=(pose,bg)=>{draw(38);for(const [,l,num] of bars){l.visible=false;num.visible=false;}scene.background=null;renderer.setClearColor(0,0);document.body.style.backgroundImage='url('+bg+')';document.body.style.backgroundSize='100% 100%';
 const matrix=new THREE.Matrix4().set(...pose);cam.matrixAutoUpdate=false;cam.matrixWorldAutoUpdate=false;cam.matrixWorldInverse.copy(matrix);cam.matrixWorld.copy(matrix).invert();cam.projectionMatrix.set(2*700/640,0,0,0,0,2*700/480,0,0,0,0,-1.0002,-.020002,0,0,-1,0);cam.projectionMatrixInverse.copy(cam.projectionMatrix).invert();
 heading.textContent='District 3 on the tabletop';caption.textContent='Marker-tracked AR • The forecast and the observed surge';renderer.render(scene,cam)};
if(navigator.xr)navigator.xr.isSessionSupported('immersive-ar').then(ok=>{ar.hidden=!ok});
ar.onclick=async()=>{
 const session=await navigator.xr.requestSession('immersive-ar',{requiredFeatures:['hit-test']});
 const viewer=await session.requestReferenceSpace('viewer'), hits=await session.requestHitTestSource({space:viewer});
 scene.background=null;renderer.setClearColor(0,0);world.visible=false;
 await renderer.xr.setSession(session);
 session.addEventListener('select',event=>{
  const hit=event.frame.getHitTestResults(hits)[0];if(!hit)return;
  const pose=hit.getPose(renderer.xr.getReferenceSpace());if(!pose)return;
  const {x,y,z}=pose.transform.position;world.position.set(x,y+.025,z);world.scale.setScalar(.035);world.visible=true;
 });
 session.addEventListener('end',()=>{hits.cancel();world.visible=true;world.position.set(0,0,0);world.scale.setScalar(1);scene.background=new THREE.Color(sky)});
};
