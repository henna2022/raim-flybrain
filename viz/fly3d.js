// Procedural Drosophila model for the museum exhibit. Three.js r128, plain script.
window.createFly = function (THREE) {
  'use strict';
  var object = new THREE.Group();
  object.name = 'fruitFly';
  function mat(color, opts) {
    var s = { color: color, roughness: 0.72, metalness: 0.02 }, k;
    opts = opts || {}; for (k in opts) s[k] = opts[k];
    return new THREE.MeshStandardMaterial(s);
  }
  var tan = mat(0xc49a5a), amber = mat(0xa9773e), dark = mat(0x3b2518);
  var black = mat(0x17110d), mouthMat = mat(0x5b3028);
  var eyeMat = mat(0xd81e1e, { roughness: 0.38, emissive: 0x3a0303, flatShading: true });
  var wingMat = mat(0xd9eff4, { transparent: true, opacity: 0.34, side: THREE.DoubleSide, depthWrite: false, roughness: 0.3 });
  var veinMat = new THREE.LineBasicMaterial({ color: 0x7f9aa0, transparent: true, opacity: 0.72 });
  var hairMat = new THREE.LineBasicMaterial({ color: 0x352219 });
  var sphere18 = new THREE.SphereGeometry(1, 18, 12);
  var sphere12 = new THREE.SphereGeometry(1, 12, 8);
  var cylinder8 = new THREE.CylinderGeometry(1, 1, 1, 8, 1);
  var cylinder6 = new THREE.CylinderGeometry(1, 1, 1, 6, 1);
  function mesh(g, m, name, parent) {
    var x = new THREE.Mesh(g, m); x.name = name; (parent || object).add(x); return x;
  }
  function ellipsoid(name, x, y, z, sx, sy, sz, m, parent) {
    var e = mesh(sphere18, m, name, parent);
    e.position.set(x, y, z); e.scale.set(sx, sy, sz); return e;
  }

  // Tapered, striped shell: the tail points toward +z and the head faces -z.
  var abdomen = new THREE.Group(); abdomen.name = 'abdomen'; object.add(abdomen);
  var ap = [
    [-0.01,.69,.25,.43,.39,.39,amber], [0,.68,.52,.41,.36,.35,dark],
    [0,.66,.73,.37,.33,.31,tan], [0,.64,.91,.33,.29,.27,dark],
    [0,.62,1.08,.28,.25,.24,tan], [0,.60,1.23,.21,.19,.22,dark],
    [0,.59,1.36,.12,.12,.18,amber]
  ], i, p;
  for (i = 0; i < ap.length; i++) {
    p = ap[i]; ellipsoid('abdomenSegment' + i, p[0],p[1],p[2],p[3],p[4],p[5],p[6],abdomen);
  }
  var thorax = ellipsoid('thorax', 0,.72,-.27,.49,.48,.58,tan); thorax.rotation.x = -.06;
  var headPivot = new THREE.Group(); headPivot.name = 'headPivot';
  headPivot.position.set(0,.75,-.72); object.add(headPivot);
  ellipsoid('head',0,0,-.19,.39,.36,.38,amber,headPivot);
  var eyeL = ellipsoid('leftCompoundEye',-.30,.04,-.32,.205,.245,.19,eyeMat,headPivot);
  var eyeR = ellipsoid('rightCompoundEye',.30,.04,-.32,.205,.245,.19,eyeMat,headPivot);
  eyeL.rotation.z = -.12; eyeR.rotation.z = .12;

  var proboscis = new THREE.Group(); proboscis.name = 'proboscis';
  proboscis.position.set(0,-.24,-.35); proboscis.rotation.x = .34; headPivot.add(proboscis);
  var probStem = mesh(cylinder8,mouthMat,'proboscisStem',proboscis);
  probStem.position.y = -.105; probStem.scale.set(.045,.21,.045);
  var labellum = ellipsoid('labellum',0,-.225,0,.095,.055,.075,mouthMat,proboscis);

  // Short antennae end in branched aristae.
  var antennae = [], side;
  for (side = -1; side <= 1; side += 2) {
    var ant = new THREE.Group(); ant.name = side < 0 ? 'leftAntenna' : 'rightAntenna';
    ant.position.set(side*.13,.15,-.50); ant.rotation.z = side*-.16; headPivot.add(ant);
    var stalk = mesh(cylinder6,dark,'antennaStalk',ant);
    stalk.position.set(side*.025,.025,-.075); stalk.scale.set(.025,.15,.025); stalk.rotation.x = Math.PI*.5;
    ellipsoid('antennaClub',side*.025,.025,-.16,.055,.06,.075,dark,ant);
    var av = [
      side*.025,.04,-.20, side*.15,.10,-.38,
      side*.07,.06,-.26, side*.16,.18,-.33,
      side*.095,.075,-.30, side*.19,.08,-.34,
      side*.12,.085,-.34, side*.19,0,-.36
    ];
    var ag = new THREE.BufferGeometry();
    ag.setAttribute('position',new THREE.Float32BufferAttribute(av,3));
    var arista = new THREE.LineSegments(ag,hairMat); arista.name = 'featheryArista'; ant.add(arista);
    antennae.push(ant);
  }

  // Softly pointed translucent wings and a fixed vein network.
  var ws = new THREE.Shape(); ws.moveTo(0,0);
  ws.bezierCurveTo(.34,-.05,.65,.12,.78,.40);
  ws.bezierCurveTo(.88,.74,.55,1.36,.12,1.55);
  ws.bezierCurveTo(-.06,1.25,-.08,.48,0,0);
  var wingGeometry = new THREE.ShapeGeometry(ws,10);
  var vg = new THREE.BufferGeometry();
  vg.setAttribute('position',new THREE.Float32BufferAttribute([
    .02,0,.004,.13,1.42,.004, .02,.05,.004,.53,1.14,.004,
    .04,.10,.004,.75,.62,.004, .09,.52,.004,.68,.85,.004,
    .12,.88,.004,.48,1.20,.004
  ],3));
  var wingPivots = [];
  for (side = -1; side <= 1; side += 2) {
    var wp = new THREE.Group(); wp.name = side < 0 ? 'leftWing' : 'rightWing';
    wp.position.set(side*.24,1.02,-.38); wp.rotation.order = 'YXZ';
    wp.rotation.y = side*-.20; wp.rotation.x = Math.PI*.5; object.add(wp);
    var wing = mesh(wingGeometry,wingMat,'wingMembrane',wp); wing.scale.x = side;
    var veins = new THREE.LineSegments(vg,veinMat); veins.name = 'wingVeins'; veins.scale.x = side; wp.add(veins);
    wingPivots.push(wp);
  }

  // Six articulated legs, each with femur, tibia, tarsus, and a planted foot.
  var middleLegs = [], legZ = [-.52,-.22,.08], angles = [.96,1.15,.82], li;
  var footWorld = new THREE.Vector3(), footBox = new THREE.Box3();
  for (li = 0; li < 3; li++) for (side = -1; side <= 1; side += 2) {
    var hip = new THREE.Group();
    hip.name = (side < 0 ? 'left' : 'right') + ['FrontLeg','MiddleLeg','HindLeg'][li];
    hip.position.set(side*.30,.63,legZ[li]); hip.rotation.z = side*angles[li];
    hip.rotation.x = li === 0 ? -.38 : (li === 2 ? .48 : .05); object.add(hip);
    var femur = mesh(cylinder6,dark,'femur',hip); femur.position.y = -.24; femur.scale.set(.035,.48,.035);
    var knee = new THREE.Group(); knee.name = 'knee'; knee.position.y = -.48;
    knee.rotation.z = side*-.72; hip.add(knee);
    var tibia = mesh(cylinder6,black,'tibia',knee); tibia.position.y = -.25; tibia.scale.set(.027,.50,.027);
    var ankle = new THREE.Group(); ankle.name = 'ankle'; ankle.position.y = -.50;
    ankle.rotation.z = side*-.20; knee.add(ankle);
    var tarsus = mesh(cylinder6,dark,'tarsus',ankle); tarsus.position.y = -.115; tarsus.scale.set(.020,.23,.020);
    var foot = mesh(sphere12,black,'foot',ankle);
    foot.position.set(side*.035,-.255,-.045); foot.scale.set(.115,.025,.19);
    object.updateMatrixWorld(true); foot.getWorldPosition(footWorld);
    hip.position.y += .025 - footWorld.y;
    object.updateMatrixWorld(true); footBox.setFromObject(foot);
    hip.position.y -= footBox.min.y;
    if (li === 1) middleLegs.push(hip);
  }

  // A few readable thoracic bristles.
  var bd = [[-.28,.99,-.36,-.42],[.28,.99,-.36,.42],[-.22,1.04,-.12,-.30],
            [.22,1.04,-.12,.30],[-.18,.99,.04,-.22],[.18,.99,.04,.22]];
  for (i = 0; i < bd.length; i++) {
    var b = mesh(cylinder6,black,'thoraxBristle');
    b.position.set(bd[i][0],bd[i][1]+.065,bd[i][2]);
    b.scale.set(.010,.13,.010); b.rotation.z = bd[i][3];
  }

  // Store the exact constructed pose. update() starts from it without allocations.
  var poseObjects = [], poseValues = [];
  object.traverse(function (part) {
    poseObjects.push(part);
    poseValues.push([part.position.x,part.position.y,part.position.z,
      part.rotation.x,part.rotation.y,part.rotation.z,
      part.scale.x,part.scale.y,part.scale.z]);
  });
  var currentAction = null, actionStart = 0, actionNeedsStart = false;
  var TWO_PI = Math.PI*2;
  function clamp01(v) { return v < 0 ? 0 : (v > 1 ? 1 : v); }
  function smooth(v) { v = clamp01(v); return v*v*(3-2*v); }
  function pulse(t,a,z) { return Math.sin(clamp01((t-a)/(z-a))*Math.PI); }
  function restorePose() {
    var j, o, v;
    for (j = 0; j < poseObjects.length; j++) {
      o = poseObjects[j]; v = poseValues[j];
      o.position.set(v[0],v[1],v[2]); o.rotation.set(v[3],v[4],v[5]); o.scale.set(v[6],v[7],v[8]);
    }
  }
  function reset() {
    restorePose(); currentAction = null; actionStart = 0; actionNeedsStart = false;
  }
  function update(now) {
    var seconds = now*.001, elapsed = 0, j, k, flap, shake, hover;
    restorePose();
    if (currentAction !== null) {
      if (actionNeedsStart) { actionStart = now; actionNeedsStart = false; }
      elapsed = Math.max(0,(now-actionStart)*.001);
    }
    object.position.y = Math.sin(seconds*2.1)*.009;
    abdomen.scale.y = 1+Math.sin(seconds*2.1)*.012;
    for (j=0;j<2;j++) {
      wingPivots[j].rotation.y += (j===0?-1:1)*Math.sin(seconds*2.8)*.012;
      antennae[j].rotation.z += (j===0?-1:1)*Math.sin(seconds*3.7+j)*.025;
    }
    if (currentAction === 'extend') {
      k=smooth(elapsed/.65); headPivot.rotation.x+=k*.22; proboscis.rotation.x+=k*.26;
      probStem.scale.y*=1+k*1.65; probStem.position.y-=k*.17; labellum.position.y-=k*.35;
    } else if (currentAction === 'refuse') {
      k=1-smooth((elapsed-1.25)/.55); shake=Math.sin(elapsed*TWO_PI*2.5)*.30*k;
      headPivot.rotation.y=shake; headPivot.rotation.z=Math.sin(elapsed*TWO_PI*2.5+.7)*.035*k;
    } else if (currentAction === 'sniff') {
      k=1-smooth((elapsed-1.75)/.65);
      headPivot.rotation.y=Math.sin(elapsed*5.2)*.10*k; headPivot.rotation.x=Math.sin(elapsed*7+.5)*.055*k;
      for(j=0;j<2;j++){antennae[j].rotation.z+=(j===0?-1:1)*Math.sin(elapsed*17+j)*.14*k;antennae[j].rotation.x=Math.sin(elapsed*13+j*1.7)*.07*k;}
    } else if (currentAction === 'hesitate') {
      if(elapsed<.55) k=smooth(elapsed/.55)*.48; else if(elapsed<1.10) k=.48; else k=.48*(1-smooth((elapsed-1.10)/.65));
      probStem.scale.y*=1+k; probStem.position.y-=k*.08; labellum.position.y-=k*.17; headPivot.rotation.x+=k*.19;
      shake=pulse(elapsed,1.55,2.35); headPivot.rotation.y=Math.sin((elapsed-1.55)*11)*.13*shake;
    } else if (currentAction === 'escape') {
      if(elapsed<.18){k=smooth(elapsed/.18);object.position.y=-.08*k;for(j=0;j<2;j++)middleLegs[j].rotation.z*=1-k*.16;}
      else{k=smooth((elapsed-.18)/.82);object.position.x=-2.2*k;object.position.y=-.08+2.28*k;object.position.z=-.30*k;
        object.rotation.z=.17*Math.sin(k*Math.PI);object.rotation.x=-.16*Math.sin(k*Math.PI);
        for(j=0;j<2;j++)middleLegs[j].rotation.z*=1+.32*(1-k);}
      hover=elapsed>1?Math.sin((elapsed-1)*6)*.035:0;if(elapsed>1)object.position.y=2.2+hover;
      flap=Math.sin(elapsed*TWO_PI*24)*.92;
      for(j=0;j<2;j++){wingPivots[j].rotation.x=.18+(j===0?flap:-flap);wingPivots[j].rotation.y=(j===0?-1:1)*.66;}
    }
  }
  function act(name) { reset(); currentAction=name; actionNeedsStart=true; }
  return { object: object, act: act, reset: reset, update: update };
};
