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
  var tan = mat(0xd4ad70), amber = mat(0xba894d), dark = mat(0x513724);
  var legMat = mat(0x795435), bandMat = mat(0x65432d);
  var black = mat(0x17110d), mouthMat = mat(0x5b3028);
  var eyeMat = mat(0xf12c25, { roughness: 0.38, emissive: 0x3a0303, flatShading: true });
  var wingMat = mat(0xffffff, { vertexColors: true, transparent: true, opacity: 0.20, side: THREE.DoubleSide, depthWrite: false, roughness: 0.18, metalness: 0.16 });
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

  // Rounded pale shell, with narrow tergite margins only on the rear half.
  // Longitudinal axis is z: head negative, tail positive.
  var abdomen = new THREE.Group(); abdomen.name = 'abdomen'; object.add(abdomen);
  var i, side;
  ellipsoid('abdomenShell',0,.72,.78,.39,.34,.78,tan,abdomen);
  function shellPatch(name, start, end, material) {
    var vertices = [], indices = [], row, col, z, r, angle;
    for (row=0;row<=4;row++) {
      z=start+(end-start)*row/4;
      r=Math.sqrt(Math.max(0,1-Math.pow((z-.78)/.78,2)));
      for(col=0;col<=32;col++) {
        angle=col*Math.PI*2/32;
        vertices.push((.39*r+.0015)*Math.cos(angle),
          .72+(.34*r+.0015)*Math.sin(angle),z);
        if(row<4 && col<32) {
          var n=row*33+col;
          indices.push(n,n+1,n+33,n+1,n+34,n+33);
        }
      }
    }
    var g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
    g.setIndex(indices); g.computeVertexNormals();
    mesh(g,material,name,abdomen);
  }
  shellPatch('rearBand1',.91,.937,bandMat);
  shellPatch('rearBand2',1.12,1.148,bandMat);
  shellPatch('rearBand3',1.31,1.338,bandMat);
  shellPatch('darkTailTip',1.46,1.56,bandMat);
  var thorax = ellipsoid('thorax', 0,.72,-.27,.49,.48,.58,tan); thorax.rotation.x = -.06;
  var headPivot = new THREE.Group(); headPivot.name = 'headPivot';
  headPivot.position.set(0,.75,-.72); object.add(headPivot);
  ellipsoid('head',0,0,-.19,.30,.32,.32,amber,headPivot);
  var eyeL = ellipsoid('leftCompoundEye',-.255,.04,-.32,.225,.29,.235,eyeMat,headPivot);
  var eyeR = ellipsoid('rightCompoundEye',.255,.04,-.32,.225,.29,.235,eyeMat,headPivot);
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

  // Long clear wings fold flat, inward across the back, beyond the tail.
  var ws = new THREE.Shape(); ws.moveTo(0,0);
  ws.bezierCurveTo(.24,.04,.49,.43,.49,.95);
  ws.bezierCurveTo(.51,1.65,.30,2.28,.12,2.38);
  ws.bezierCurveTo(-.12,2.28,-.13,.65,0,0);
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
    wp.position.set(side*.19,1.235+(side>0?.012:0),-.38); wp.rotation.order = 'YXZ';
    wp.rotation.y = side*-.16; wp.rotation.x = Math.PI*.5; object.add(wp);
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
    var femur = mesh(cylinder6,legMat,'femur',hip); femur.position.y = -.24; femur.scale.set(.027,.48,.027);
    var knee = new THREE.Group(); knee.name = 'knee'; knee.position.y = -.48;
    knee.rotation.z = side*-.72; hip.add(knee);
    var tibia = mesh(cylinder6,legMat,'tibia',knee); tibia.position.y = -.25; tibia.scale.set(.020,.50,.020);
    var hairs = [], h;
    for(h=0;h<6;h++) {
      var hy=-.07-h*.075;
      hairs.push(.016,hy,0,.055,hy-.035,.014,
        -.016,hy,0,-.05,hy-.025,-.012);
    }
    var hg=new THREE.BufferGeometry();
    hg.setAttribute('position',new THREE.Float32BufferAttribute(hairs,3));
    var legHairs=new THREE.LineSegments(hg,hairMat); legHairs.name='legBristles'; knee.add(legHairs);
    var ankle = new THREE.Group(); ankle.name = 'ankle'; ankle.position.y = -.50;
    ankle.rotation.z = side*-.20; knee.add(ankle);
    var tarsus = mesh(cylinder6,legMat,'tarsus',ankle); tarsus.position.y = -.115; tarsus.scale.set(.020,.23,.020);
    var foot = mesh(sphere12,black,'foot',ankle);
    foot.position.set(side*.035,-.255,-.045); foot.scale.set(.045,.020,.10);
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
    b.position.set(bd[i][0],bd[i][1]+.20,bd[i][2]);
    b.scale.set(.010,.13,.010); b.rotation.z = bd[i][3];
  }

  // Muted longitudinal thoracic markings follow the curved dorsal surface.
  var pattern = [], stripe, step;
  for(stripe=-1;stripe<=1;stripe+=2) for(step=0;step<18;step++) {
    var z0=-.64+step*.035, z1=z0+.035, px=stripe*.14;
    pattern.push(px,.72+.48*Math.sqrt(1-px*px/(.49*.49)-Math.pow((z0+.27)/.58,2))+.007,z0,
      px,.72+.48*Math.sqrt(1-px*px/(.49*.49)-Math.pow((z1+.27)/.58,2))+.007,z1);
  }
  var pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.Float32BufferAttribute(pattern,3));
  var markings=new THREE.LineSegments(pg,new THREE.LineBasicMaterial({color:0x825b36,transparent:true,opacity:.55}));
  markings.name='thoraxMarkings'; object.add(markings);

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
      k=smooth(elapsed/.65); headPivot.rotation.x+=k*.22; proboscis.rotation.x+=k*.55;
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
