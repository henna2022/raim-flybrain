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
  var tan = mat(0xcf9f62), amber = mat(0xb8874a), faceMat = mat(0xc4955a);
  var legMat = mat(0xb5874c), bandMat = mat(0x654027), rearMat = mat(0x513321), tailMat = mat(0x3e291d);
  var mouthMat = mat(0x5b3028);
  var eyeMat = mat(0xff241c, { roughness: 0.38, emissive: 0x580503, flatShading: true });
  var wingMat = mat(0xe5e5e1, { vertexColors: true, transparent: true, opacity: 0.30, side: THREE.DoubleSide, depthWrite: false, roughness: 0.18, metalness: 0.16 });
  var veinMat = new THREE.LineBasicMaterial({ color: 0x8a7a5a, transparent: true, opacity: 0.70 });
  var hairMat = new THREE.LineBasicMaterial({ color: 0x795435, transparent: true, opacity: 0.65 });
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

  // Longitudinal axis is z: head negative, tail positive.
  // A compact oval shell; broad dorsal tergite bands leave the belly tan.
  var abdomen = new THREE.Group(); abdomen.name = 'abdomen'; object.add(abdomen);
  var i, side;
  function shellPatch(name, start, end, material, dorsal) {
    var vertices = [], indices = [], row, col, z, r, angle, u;
    var rows=dorsal?3:(name==='abdomenShell'?18:6), cols=24, lift=name==='abdomenShell'?0:.002;
    for (row=0;row<=rows;row++) {
      z=start+(end-start)*row/rows; u=(z-.64)/.60;
      r=Math.sqrt(Math.max(0,1-u*u))*(1-.12*u);
      for(col=0;col<=cols;col++) {
        angle=dorsal?-.12+col*(Math.PI+.24)/cols:col*Math.PI*2/cols;
        vertices.push((.39*r+lift)*Math.cos(angle),
          .72+(.31*r+lift)*Math.sin(angle),z);
        if(row<rows && col<cols) {
          var n=row*(cols+1)+col;
          indices.push(n,n+1,n+cols+1,n+1,n+cols+2,n+cols+1);
        }
      }
    }
    var g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
    g.setIndex(indices); g.computeVertexNormals();
    mesh(g,material,name,abdomen);
  }
  shellPatch('abdomenShell',.04,1.24,tan,false);
  shellPatch('rearBand1',.35,.47,bandMat,true);
  shellPatch('rearBand2',.60,.76,rearMat,true);
  shellPatch('rearBand3',.88,1.07,tailMat,true);
  shellPatch('darkTailTip',1.12,1.24,tailMat,false);
  var thorax = ellipsoid('thorax', 0,.76,-.27,.37,.38,.49,amber); thorax.rotation.x = -.14;
  var headPivot = new THREE.Group(); headPivot.name = 'headPivot';
  headPivot.position.set(0,.75,-.72); object.add(headPivot);
  ellipsoid('head',0,0,-.19,.24,.265,.255,faceMat,headPivot);
  ellipsoid('paleFace',0,-.025,-.405,.115,.19,.065,faceMat,headPivot);
  var eyeL = ellipsoid('leftCompoundEye',-.205,.035,-.245,.175,.265,.225,eyeMat,headPivot);
  var eyeR = ellipsoid('rightCompoundEye',.205,.035,-.245,.175,.265,.225,eyeMat,headPivot);
  eyeL.rotation.z = -.12; eyeR.rotation.z = .12;

  var proboscis = new THREE.Group(); proboscis.name = 'proboscis'; proboscis.visible = false;
  proboscis.position.set(0,-.24,-.35); proboscis.rotation.x = .34; headPivot.add(proboscis);
  var probStem = mesh(cylinder8,mouthMat,'proboscisStem',proboscis);
  probStem.position.y = -.105; probStem.scale.set(.045,.21,.045);
  var labellum = ellipsoid('labellum',0,-.225,0,.095,.055,.075,mouthMat,proboscis);

  // Tiny facial antennae carry fine, laterally branching aristae.
  var antennae = [];
  for (side = -1; side <= 1; side += 2) {
    var ant = new THREE.Group(); ant.name = side < 0 ? 'leftAntenna' : 'rightAntenna';
    ant.position.set(side*.065,.095,-.445); ant.rotation.z = side*-.16; headPivot.add(ant);
    var stalk = mesh(cylinder6,amber,'antennaStalk',ant);
    stalk.position.set(side*.008,0,-.018); stalk.scale.set(.012,.036,.012); stalk.rotation.x = Math.PI*.5;
    ellipsoid('antennaClub',side*.010,-.009,-.044,.023,.032,.025,amber,ant);
    var av = [
      side*.018,.012,-.055, side*.135,.105,-.085,
      side*.044,.033,-.062, side*.045,.077,-.065,
      side*.068,.052,-.068, side*.105,.039,-.092,
      side*.090,.070,-.074, side*.095,.115,-.078,
      side*.111,.087,-.080, side*.145,.078,-.100
    ];
    var ag = new THREE.BufferGeometry();
    ag.setAttribute('position',new THREE.Float32BufferAttribute(av,3));
    var arista = new THREE.LineSegments(ag,hairMat); arista.name = 'featheryArista'; ant.add(arista);
    antennae.push(ant);
  }

  // Long clear wings fold flat, inward across the back, beyond the tail.
  var ws = new THREE.Shape(); ws.moveTo(0,0);
  ws.bezierCurveTo(.24,.04,.49,.43,.49,.95);
  ws.bezierCurveTo(.51,1.65,.34,2.38,.12,2.38);
  ws.bezierCurveTo(-.10,2.38,-.13,.65,0,0);
  var wingGeometry = new THREE.ShapeGeometry(ws,18);
  // Quiet lavender-to-mint sheen under the transparent membrane.
  var wingColors=[], wingPositions=wingGeometry.attributes.position;
  for(i=0;i<wingPositions.count;i++) {
    var sheen=.5+.5*Math.sin(wingPositions.getY(i)*4+wingPositions.getX(i)*6);
    wingColors.push(.87+.10*sheen,.94-.07*sheen,1-.04*sheen);
  }
  wingGeometry.setAttribute('color',new THREE.Float32BufferAttribute(wingColors,3));
  var vg = new THREE.BufferGeometry();
  vg.setAttribute('position',new THREE.Float32BufferAttribute([
    .02,.06,-.004,.12,2.31,-.004,
    .02,.06,-.004,.28,.65,-.004, .28,.65,-.004,.38,1.55,-.004,
    .38,1.55,-.004,.22,2.22,-.004,
    .02,.06,-.004,.08,.78,-.004, .08,.78,-.004,.24,1.62,-.004,
    .24,1.62,-.004,.17,2.30,-.004,
    .02,.06,-.004,-.06,.90,-.004, -.06,.90,-.004,.04,2.13,-.004,
    .08,.78,-.004,.30,.83,-.004, .20,1.45,-.004,.39,1.48,-.004
  ],3));
  var wingPivots = [];
  for (side = -1; side <= 1; side += 2) {
    var wp = new THREE.Group(); wp.name = side < 0 ? 'leftWing' : 'rightWing';
    wp.position.set(side*.14,1.15+(side>0?.012:0),-.30); wp.rotation.order = 'YXZ';
    wp.scale.set(.86,.72,1); wp.rotation.y = side*-.19; wp.rotation.x = Math.PI*.5; object.add(wp);
    var wing = mesh(wingGeometry,wingMat,'wingMembrane',wp); wing.scale.x = side;
    var veins = new THREE.LineSegments(vg,veinMat); veins.name = 'wingVeins'; veins.scale.x = side; wp.add(veins);
    wingPivots.push(wp);
  }

  // Short legs radiate forward, sideways and back; raised knees form a wide stance.
  var middleLegs = [], legZ = [-.52,-.22,.08], angles = [1.78,1.82,1.78], li;
  var footWorld = new THREE.Vector3(), footBox = new THREE.Box3();
  for (li = 0; li < 3; li++) for (side = -1; side <= 1; side += 2) {
    var hip = new THREE.Group();
    hip.name = (side < 0 ? 'left' : 'right') + ['FrontLeg','MiddleLeg','HindLeg'][li];
    hip.position.set(side*.25,.46,legZ[li]); hip.rotation.order = 'YZX';
    hip.rotation.z = side*angles[li];
    hip.rotation.y = side*(li === 0 ? .70 : (li === 2 ? -.78 : 0)); object.add(hip);
    var femur = mesh(cylinder6,legMat,'femur',hip); femur.position.y = -.18; femur.scale.set(.022,.36,.022);
    var knee = new THREE.Group(); knee.name = 'knee'; knee.position.y = -.36;
    knee.rotation.z = side*-1.55; hip.add(knee);
    var tibia = mesh(cylinder6,legMat,'tibia',knee); tibia.position.y = -.1875; tibia.scale.set(.016,.375,.016);
    var hairs = [], h;
    for(h=0;h<2;h++) {
      var hy=-.10-h*.15;
      hairs.push(.016,hy,0,.035,hy-.025,.008,
        -.016,hy,0,-.032,hy-.02,-.008);
    }
    var hg=new THREE.BufferGeometry();
    hg.setAttribute('position',new THREE.Float32BufferAttribute(hairs,3));
    var legHairs=new THREE.LineSegments(hg,hairMat); legHairs.name='legBristles'; knee.add(legHairs);
    var ankle = new THREE.Group(); ankle.name = 'ankle'; ankle.position.y = -.375;
    ankle.rotation.z = side*-.10; knee.add(ankle);
    var tarsus = mesh(cylinder6,legMat,'tarsus',ankle); tarsus.position.y = -.086; tarsus.scale.set(.012,.172,.012);
    var foot = mesh(sphere12,legMat,'foot',ankle);
    foot.position.set(side*.025,-.19,-.030); foot.scale.set(.022,.016,.055);
    object.updateMatrixWorld(true); foot.getWorldPosition(footWorld);
    hip.position.y += .025 - footWorld.y;
    object.updateMatrixWorld(true); footBox.setFromObject(foot);
    hip.position.y -= footBox.min.y;
    if (li === 1) middleLegs.push(hip);
  }

  // Just four fine bristles on the tan dome, without thoracic stripes.
  var bg = new THREE.BufferGeometry();
  bg.setAttribute('position',new THREE.Float32BufferAttribute([
    -.23,1.04,-.40,-.26,1.11,-.42, .23,1.04,-.40,.26,1.11,-.42,
    -.20,1.06,-.12,-.23,1.13,-.10, .20,1.06,-.12,.23,1.13,-.10
  ],3));
  var bristles = new THREE.LineSegments(bg,hairMat); bristles.name='thoraxBristles'; object.add(bristles);

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
    proboscis.visible = false;
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
      k=smooth(elapsed/.65); proboscis.visible=k>0; proboscis.scale.y=k; headPivot.rotation.x+=k*.22; proboscis.rotation.x+=k*.55;
      probStem.scale.y*=1+k*2.8; probStem.position.y-=k*.294; labellum.position.y-=k*.588;
    } else if (currentAction === 'refuse') {
      k=1-smooth((elapsed-1.25)/.55); shake=Math.sin(elapsed*TWO_PI*2.5)*.30*k;
      headPivot.rotation.y=shake; headPivot.rotation.z=Math.sin(elapsed*TWO_PI*2.5+.7)*.035*k;
    } else if (currentAction === 'sniff') {
      k=1-smooth((elapsed-1.75)/.65);
      headPivot.rotation.y=Math.sin(elapsed*5.2)*.10*k; headPivot.rotation.x=Math.sin(elapsed*7+.5)*.055*k;
      for(j=0;j<2;j++){antennae[j].rotation.z+=(j===0?-1:1)*Math.sin(elapsed*17+j)*.14*k;antennae[j].rotation.x=Math.sin(elapsed*13+j*1.7)*.07*k;}
    } else if (currentAction === 'hesitate') {
      if(elapsed<.55) k=smooth(elapsed/.55)*.48; else if(elapsed<1.10) k=.48; else k=.48*(1-smooth((elapsed-1.10)/.65));
      proboscis.visible=k>0; proboscis.scale.y=k;
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
