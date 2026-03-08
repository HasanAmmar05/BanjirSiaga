let currentMode='live',map=null,marker=null,selectedLat=null,selectedLon=null,uploadedFile=null;

    // Subtle water ripple
    const canvas=document.getElementById('ripple-canvas'),ctx=canvas.getContext('2d');
    let time=0;
    function initCanvas(){canvas.width=window.innerWidth;canvas.height=window.innerHeight;}
    function drawRipples(){
        ctx.clearRect(0,0,canvas.width,canvas.height);
        for(let i=0;i<3;i++){
            const y=canvas.height*(0.3+i*0.25)+Math.sin(time*0.5+i)*20;
            ctx.beginPath();
            ctx.moveTo(0,y);
            for(let x=0;x<canvas.width;x+=5){
                ctx.lineTo(x,y+Math.sin(x*0.005+time*(0.3+i*0.1))*8+Math.sin(x*0.01+time*0.2)*4);
            }
            ctx.strokeStyle=`rgba(45,212,191,${0.06-i*0.015})`;
            ctx.lineWidth=1;
            ctx.stroke();
        }
        time+=0.02;
        requestAnimationFrame(drawRipples);
    }
    initCanvas();drawRipples();
    window.addEventListener('resize',initCanvas);

    function showScreen(id){
        document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        if(id==='screen-input'&&!map)initMap();
        window.scrollTo(0,0);
    }

    function initMap(){
        setTimeout(()=>{
            map=L.map('map').setView([3.15,101.71],11);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'CartoDB',maxZoom:19}).addTo(map);
            map.on('click',e=>{
                selectedLat=e.latlng.lat;selectedLon=e.latlng.lng;
                if(marker)map.removeLayer(marker);
                marker=L.marker(e.latlng).addTo(map);
                document.getElementById('locationInput').value=`${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
            });
        },100);
    }

    function toggleReplayMode(){
        currentMode=currentMode==='live'?'replay':'live';
        const t=document.getElementById('replayToggle'),b=document.getElementById('replayBadge');
        if(currentMode==='replay'){t.classList.add('active');b.classList.add('visible');}
        else{t.classList.remove('active');b.classList.remove('visible');}
    }

    function quickSearch(p){document.getElementById('locationInput').value=p;selectedLat=null;selectedLon=null;}

    async function submitAssessment(){
        const loc=document.getElementById('locationInput').value.trim();
        if(!loc){alert('Please enter a location');return;}
        showScreen('screen-loading');
        document.getElementById('loadingLocation').textContent=loc;
        const fill=document.getElementById('loaderFill');
        const steps=['step1','step2','step3'];
        for(let i=0;i<3;i++){
            await new Promise(r=>setTimeout(r,500));
            fill.style.width=((i+1)*33)+'%';
            const el=document.getElementById(steps[i]);
            el.style.opacity='1';el.classList.add('active');
            if(i>0){const p=document.getElementById(steps[i-1]);p.classList.remove('active');p.classList.add('done');}
        }
        try{
            const payload={location:loc,mode:currentMode};
            if(selectedLat){payload.lat=selectedLat;payload.lon=selectedLon;}
            const resp=await fetch('/api/assess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
            if(!resp.ok){const er=await resp.json();throw new Error(er.detail||'Error');}
            const data=await resp.json();
            document.getElementById('step3').classList.remove('active');
            document.getElementById('step3').classList.add('done');
            fill.style.width='100%';
            await new Promise(r=>setTimeout(r,300));
            renderResult(data);
        }catch(e){alert('Error: '+e.message);showScreen('screen-input');}
        steps.forEach(s=>{const el=document.getElementById(s);el.style.opacity=s==='step1'?'1':'0.4';el.classList.remove('active','done');});
        fill.style.width='0%';
    }

    function renderResult(d){
        const loc=(d.location||'').split(',').slice(0,2).join(', ');
        document.getElementById('resultLocation').textContent=loc;
        document.getElementById('resultTimestamp').textContent=new Date().toLocaleString('en-MY',{dateStyle:'medium',timeStyle:'short'})+' MYT';
        const risk=(d.risk_level||'WASPADA').toUpperCase();
        const badge=document.getElementById('riskBadge');
        const cfg={
            SELAMAT:{cls:'risk-safe',sub:'Low risk — area is currently safe'},
            WASPADA:{cls:'risk-warn',sub:'Moderate risk — exercise caution'},
            BAHAYA:{cls:'risk-danger',sub:'High risk — immediate action required'}
        }[risk]||{cls:'risk-warn',sub:'Moderate risk'};
        badge.className=cfg.cls;badge.style.cssText='border-radius:var(--radius-lg);padding:28px;text-align:center;margin-bottom:16px;';
        document.getElementById('riskLevel').textContent=risk;
        document.getElementById('riskSubtext').textContent=cfg.sub;
        const wx=d.weather||{};
        document.getElementById('wxRain').textContent=(wx.current_rain_mm||0)+'mm';
        document.getElementById('wxHumidity').textContent=(wx.humidity_pct||0)+'%';
        document.getElementById('wxWind').textContent=(wx.wind_speed_kmh||0)+'km/h';
        document.getElementById('assessBM').textContent=d.bm||'Tiada maklumat';
        document.getElementById('assessEN').textContent=d.en||'No information';
        const al=document.getElementById('actionsList');al.innerHTML='';
        (d.immediate_actions||[]).forEach(a=>{const s=document.createElement('span');s.className='pill';s.textContent=a;al.appendChild(s);});
        const es=document.getElementById('evacSection'),el=document.getElementById('evacList');el.innerHTML='';
        if(d.evacuation_centres&&d.evacuation_centres.length>0){
            es.style.display='block';
            d.evacuation_centres.forEach(c=>{
                const cd=document.createElement('div');
                cd.className='card evac-card';
                cd.style.padding='14px 14px 14px 24px';
                cd.innerHTML=`<div class="heading" style="font-size:0.8125rem;">${c.name}</div>
                    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px;">${c.address}</div>
                    <div style="display:flex;gap:16px;margin-top:6px;">
                        <span class="mono" style="font-size:0.6875rem;color:var(--accent-teal);">${c.distance_km}km</span>
                        <span style="font-size:0.6875rem;color:var(--text-muted);">Capacity: ${c.capacity}</span>
                    </div>`;
                el.appendChild(cd);
            });
        }else{es.style.display='none';}
        showScreen('screen-result');
    }

    // Photo
    const dz=document.getElementById('dropZone');
    dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('dragover');});
    dz.addEventListener('dragleave',()=>dz.classList.remove('dragover'));
    dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('dragover');if(e.dataTransfer.files.length)handlePhotoFile(e.dataTransfer.files[0]);});
    function handlePhotoUpload(e){if(e.target.files.length)handlePhotoFile(e.target.files[0]);}
    function handlePhotoFile(f){
        uploadedFile=f;
        const r=new FileReader();
        r.onload=e=>{document.getElementById('previewImg').src=e.target.result;document.getElementById('photoPreview').style.display='block';document.getElementById('dropZone').style.display='none';document.getElementById('photoResult').style.display='none';};
        r.readAsDataURL(f);
    }
    async function analyzePhoto(){
        if(!uploadedFile)return;
        const b=document.getElementById('analyzeBtn');b.textContent='Analyzing...';b.disabled=true;
        const fd=new FormData();fd.append('file',uploadedFile);fd.append('location',document.getElementById('locationInput')?.value||'Kuala Lumpur');
        try{const r=await fetch('/api/photo',{method:'POST',body:fd});if(!r.ok){const e=await r.json();throw new Error(e.detail||'Error');}renderPhotoResult(await r.json());}
        catch(e){alert('Error: '+e.message);}
        b.textContent='Analyze with Gemini Vision';b.disabled=false;
    }
    function renderPhotoResult(d){
        const risk=(d.risk_level||'WASPADA').toUpperCase();
        const cfg={SELAMAT:{cls:'risk-safe'},WASPADA:{cls:'risk-warn'},BAHAYA:{cls:'risk-danger'}}[risk]||{cls:'risk-warn'};
        const pb=document.getElementById('photoRiskBadge');
        pb.className=cfg.cls;pb.style.cssText='border-radius:var(--radius);padding:20px;text-align:center;margin-bottom:16px;';
        document.getElementById('photoRiskLevel').textContent=risk;
        document.getElementById('photoDepth').textContent=d.depth_estimate||'N/A';
        document.getElementById('photoBM').textContent=d.bm||'';
        document.getElementById('photoEN').textContent=d.en||'';
        document.getElementById('photoAction').textContent=d.action||'';
        document.getElementById('photoResult').style.display='block';
    }
    function goBackFromPhoto(){
        document.getElementById('photoPreview').style.display='none';
        document.getElementById('photoResult').style.display='none';
        document.getElementById('dropZone').style.display='block';
        uploadedFile=null;showScreen('screen-result');
    }
    document.getElementById('locationInput')?.addEventListener('keydown',e=>{if(e.key==='Enter')submitAssessment();});