/** @odoo-module **/
/**
 * EDM PDF Annotator
 * Professional PDF annotation: highlight, underline, strikethrough,
 * sticky note, rectangle, free drawing, arrows.
 * Uses PDF.js (loaded from CDN inside the overlay).
 */

// ---------------------------------------------------------------
// 1.  Build the overlay DOM once and attach to <body>
// ---------------------------------------------------------------
function buildOverlay() {
    if (document.getElementById('edm-pdf-annotator-overlay')) return;

    const html = `
<div id="edm-pdf-annotator-overlay">

    <!-- TOOLBAR -->
    <div id="edm-annotator-toolbar">

        <div class="edm-tb-section">
            <div class="edm-tb-pagenav">
                <button class="edm-tool-btn icon" id="edm-prev-page" title="Previous page"><i class="fa fa-chevron-left"></i></button>
                <span id="edm-page-info">Page 1 / 1</span>
                <button class="edm-tool-btn icon" id="edm-next-page" title="Next page"><i class="fa fa-chevron-right"></i></button>
            </div>
            <button class="edm-tool-btn icon" id="edm-zoom-out" title="Zoom out"><i class="fa fa-search-minus"></i></button>
            <button class="edm-tool-btn icon" id="edm-zoom-in" title="Zoom in"><i class="fa fa-search-plus"></i></button>
        </div>

        <div class="edm-tb-section edm-tb-center">
            <button class="edm-tool-btn" id="edm-tool-select" title="Select / Pan"><i class="fa fa-mouse-pointer"></i> Select</button>

            <div class="edm-dd">
                <button type="button" class="edm-dd-trigger edm-tool-btn"><i class="fa fa-paint-brush"></i> Markup <i class="fa fa-caret-down"></i></button>
                <div class="edm-dd-panel">
                    <button class="edm-dd-item" id="edm-tool-highlight"><i class="fa fa-paint-brush"></i> Highlight</button>
                    <button class="edm-dd-item" id="edm-tool-underline"><i class="fa fa-underline"></i> Underline</button>
                    <button class="edm-dd-item" id="edm-tool-strikethrough"><i class="fa fa-strikethrough"></i> Strikethrough</button>
                </div>
            </div>

            <div class="edm-dd">
                <button type="button" class="edm-dd-trigger edm-tool-btn"><i class="fa fa-object-group"></i> Shapes <i class="fa fa-caret-down"></i></button>
                <div class="edm-dd-panel">
                    <button class="edm-dd-item" id="edm-tool-rectangle"><i class="fa fa-square-o"></i> Rectangle</button>
                    <button class="edm-dd-item" id="edm-tool-square"><i class="fa fa-stop"></i> Square</button>
                    <button class="edm-dd-item" id="edm-tool-ellipse"><i class="fa fa-circle-o"></i> Circle / Ellipse</button>
                    <button class="edm-dd-item" id="edm-tool-cloud"><i class="fa fa-cloud"></i> Cloud</button>
                    <button class="edm-dd-item" id="edm-tool-line"><i class="fa fa-minus"></i> Line</button>
                    <button class="edm-dd-item" id="edm-tool-arrow"><i class="fa fa-long-arrow-right"></i> Arrow</button>
                    <button class="edm-dd-item" id="edm-tool-darrow"><i class="fa fa-arrows-h"></i> Double Arrow</button>
                </div>
            </div>

            <div class="edm-dd">
                <button type="button" class="edm-dd-trigger edm-tool-btn"><i class="fa fa-plus-square-o"></i> Insert <i class="fa fa-caret-down"></i></button>
                <div class="edm-dd-panel">
                    <button class="edm-dd-item" id="edm-tool-text"><i class="fa fa-font"></i> Text box</button>
                    <button class="edm-dd-item" id="edm-tool-note"><i class="fa fa-sticky-note-o"></i> Sticky note</button>
                    <button class="edm-dd-item" id="edm-tool-stamp"><i class="fa fa-certificate"></i> Stamp</button>
                    <button class="edm-dd-item" id="edm-tool-signature"><i class="fa fa-pencil-square-o"></i> Signature</button>
                    <div class="edm-dd-row"><span>Stamp text</span>
                        <select id="edm-stamp-select">
                            <option value="APPROVED">APPROVED</option>
                            <option value="REJECTED">REJECTED</option>
                            <option value="DRAFT">DRAFT</option>
                            <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                            <option value="REVIEWED">REVIEWED</option>
                        </select>
                    </div>
                </div>
            </div>

            <button class="edm-tool-btn" id="edm-tool-drawing" title="Free drawing"><i class="fa fa-pencil"></i> Draw</button>

            <div class="edm-tb-color">
                <input type="color" id="edm-color-picker" value="#FFFF00" title="Colour">
                <input type="range" id="edm-opacity-slider" min="10" max="100" value="50" title="Opacity">
            </div>
        </div>

        <div class="edm-tb-section">
            <button class="edm-tool-btn" id="edm-undo" title="Undo last annotation"><i class="fa fa-undo"></i> Undo</button>
            <button class="edm-tool-btn" id="edm-redo" title="Redo"><i class="fa fa-repeat"></i> Redo</button>
            <button class="edm-tool-btn" id="edm-save-all"><i class="fa fa-save"></i> Save</button>
            <button class="edm-tool-btn" id="edm-export-btn"><i class="fa fa-download"></i> Export</button>
            <button class="edm-tool-btn" id="edm-download-pdf"><i class="fa fa-file-pdf-o"></i> Download</button>
            <button class="edm-tool-btn" id="edm-save-version"><i class="fa fa-history"></i> Save Version</button>
            <button class="edm-tool-btn" id="edm-share-pdf"><i class="fa fa-share-alt"></i> Share</button>
            <button id="edm-close-annotator" title="Close"><i class="fa fa-times"></i></button>
        </div>
    </div>

    <!-- BODY -->
    <div id="edm-annotator-body">

        <!-- PDF canvas -->
        <div id="edm-pdf-canvas-container">
            <div id="edm-pdf-page-wrapper">
                <canvas id="edm-pdf-canvas"></canvas>
                <div id="edm-annotation-layer">
                    <svg id="edm-drawing-svg" xmlns="http://www.w3.org/2000/svg"></svg>
                </div>
            </div>
        </div>

        <!-- Sidebar -->
        <div id="edm-annotation-sidebar">
            <div id="edm-sidebar-header">
                Annotations <span id="edm-ann-count">0</span>
            </div>
            <div id="edm-desc-box">
                <div id="edm-desc-label"><i class="fa fa-align-left"></i> Description</div>
                <textarea id="edm-desc-text" placeholder="Write a description for this document..."></textarea>
                <button id="edm-desc-save"><i class="fa fa-save"></i> Save description</button>
            </div>
            <div id="edm-annotation-list"></div>
        </div>

    </div>

    <!-- Note popup -->
    <div id="edm-note-popup">
        <div style="color:#eee; font-size:12px; margin-bottom:6px;">
            <i class="fa fa-sticky-note-o"></i> Add Note
        </div>
        <textarea id="edm-note-text" placeholder="Type your note here..."></textarea>
        <div id="edm-note-popup-actions">
            <button class="edm-popup-btn save" id="edm-note-save">Save</button>
            <button class="edm-popup-btn cancel" id="edm-note-cancel">Cancel</button>
        </div>
    </div>

    <!-- Toast -->
    <div id="edm-toast"></div>

</div>`;

    document.body.insertAdjacentHTML('beforeend', html);
}

// ---------------------------------------------------------------
// 2.  Load PDF.js from CDN (once)
// ---------------------------------------------------------------
let pdfJsLoaded = false;
function ensurePdfJs(cb) {
    if (pdfJsLoaded && window.pdfjsLib) { cb(); return; }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
    script.onload = () => {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        pdfJsLoaded = true;
        cb();
    };
    document.head.appendChild(script);
}

// ---------------------------------------------------------------
// 3.  State
// ---------------------------------------------------------------
const State = {
    documentId: null,
    pdfDoc: null,
    currentPage: 1,
    totalPages: 1,
    scale: 1.5,
    currentTool: 'select',
    color: '#FFFF00',
    opacity: 0.5,
    annotations: [],        // {id, annotation_type, page_number, x,y,w,h, color,opacity,content,path_data,user_name,is_resolved}
    pendingAnnotation: null, // while dragging a rect / highlight
    isDrawing: false,
    drawPath: [],
    noteTarget: null,       // {x,y,page} where user clicked for a note
    description: '',        // free-text document description
};

// ---------------------------------------------------------------
// 4.  Helpers
// ---------------------------------------------------------------
function toast(msg, isError) {
    const el = document.getElementById('edm-toast');
    el.textContent = msg;
    el.style.background = isError ? '#c0392b' : '#27ae60';
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2200);
}

function getCsrfToken() {
    // Odoo stores csrf token in cookie "csrf_token" or window
    if (window.odoo && window.odoo.__csrf_token) return window.odoo.__csrf_token;
    const m = document.cookie.match(/csrf_token=([^;]+)/);
    return m ? m[1] : '';
}

async function rpc(route, params) {
    const resp = await fetch(route, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: 1, params }),
    });
    const data = await resp.json();
    return data.result;
}

// ---------------------------------------------------------------
// 5.  Load annotations from server
// ---------------------------------------------------------------
async function loadAnnotations() {
    const resp = await fetch(`/edm/annotation/load/${State.documentId}`);
    const data = await resp.json();
    State.annotations = data.annotations || [];
    State.description = data.description || '';
    const descEl = document.getElementById('edm-desc-text');
    if (descEl) { descEl.value = data.description || ''; }
    renderAnnotations();
    renderSidebar();
}

// ---------------------------------------------------------------
// 6.  Render PDF page
// ---------------------------------------------------------------
// Fit the page width to the visible container so the document is fully visible on load.
async function fitToWidth() {
    try {
        if (!State.pdfDoc) { return; }
        const page = await State.pdfDoc.getPage(State.currentPage || 1);
        const base = page.getViewport({ scale: 1 });
        const cont = document.getElementById('edm-pdf-canvas-container');
        if (!cont || !base.width) { return; }
        const cs = window.getComputedStyle(cont);
        const padL = parseFloat(cs.paddingLeft) || 0;
        const padR = parseFloat(cs.paddingRight) || 0;
        const avail = cont.clientWidth - padL - padR;
        if (avail > 0) {
            let s = avail / base.width;
            s = Math.max(0.5, Math.min(s, 2.5));
            State.scale = s;
        }
    } catch (e) {
        // keep default scale on failure
    }
}

async function renderPage(num) {
    const page = await State.pdfDoc.getPage(num);
    const viewport = page.getViewport({ scale: State.scale });

    const canvas = document.getElementById('edm-pdf-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    // sync annotation layer size
    const layer = document.getElementById('edm-annotation-layer');
    layer.style.width = viewport.width + 'px';
    layer.style.height = viewport.height + 'px';

    const svg = document.getElementById('edm-drawing-svg');
    svg.setAttribute('width', viewport.width);
    svg.setAttribute('height', viewport.height);
    svg.setAttribute('viewBox', `0 0 ${viewport.width} ${viewport.height}`);

    await page.render({ canvasContext: ctx, viewport }).promise;

    State.currentPage = num;
    document.getElementById('edm-page-info').textContent = `Page ${num} / ${State.totalPages}`;
    if (typeof updateStatusBar === 'function') updateStatusBar();

    renderAnnotations();
}

// ---------------------------------------------------------------
// 7.  Render annotations on the canvas layer
// ---------------------------------------------------------------
function renderAnnotations() {
    const layer = document.getElementById('edm-annotation-layer');
    const svg = document.getElementById('edm-drawing-svg');

    // clear only annotation divs (keep svg)
    layer.querySelectorAll('.edm-annotation').forEach(e => e.remove());
    // clear svg drawings
    svg.innerHTML = '';

    const canvas = document.getElementById('edm-pdf-canvas');
    const W = canvas.width;
    const H = canvas.height;

    State.annotations
        .filter(a => a.page_number === State.currentPage)
        .forEach(ann => {
            if (ann.annotation_type === 'drawing') {
                renderDrawingAnnotation(ann, svg);
                return;
            }
            if (ann.annotation_type === 'note') {
                renderNoteAnnotation(ann, layer, W, H);
                return;
            }
            if (ann.annotation_type === 'text') { renderTextAnnotation(ann, layer, W, H); return; }
            if (ann.annotation_type === 'stamp') { renderStampAnnotation(ann, layer, W, H); return; }
            if (ann.annotation_type === 'signature') { renderSignatureAnnotation(ann, layer, W, H); return; }
            renderShapeAnnotation(ann, layer, W, H);
        });
}

function buildCloudPath(w,h){var r=Math.max(6,Math.min(w,h)/8);var d='M 0 0';function side(x1,y1,x2,y2){var len=Math.hypot(x2-x1,y2-y1);var n=Math.max(1,Math.round(len/(r*2)));var dx=(x2-x1)/n,dy=(y2-y1)/n;for(var i=0;i<n;i++){d+=' A '+r.toFixed(1)+' '+r.toFixed(1)+' 0 0 1 '+(x1+dx*(i+1)).toFixed(1)+' '+(y1+dy*(i+1)).toFixed(1);}}side(0,0,w,0);side(w,0,w,h);side(w,h,0,h);side(0,h,0,0);return d+' Z';}
function buildArrowPath(w,h){var x1=2,y1=h-2,x2=w-2,y2=2,head=Math.max(8,Math.min(w,h)*0.22);return 'M '+x1+' '+y1+' L '+x2+' '+y2+' M '+x2+' '+y2+' L '+(x2-head).toFixed(1)+' '+y2+' M '+x2+' '+y2+' L '+x2+' '+(y2+head).toFixed(1);}
function buildLinePath(w,h){return 'M 2 '+(h-2)+' L '+(w-2)+' 2';}
function buildDArrowPath(w,h){var x1=2,y1=h-2,x2=w-2,y2=2,hd=Math.max(8,Math.min(w,h)*0.22);var ux=(x2-x1),uy=(y2-y1),L=Math.hypot(ux,uy)||1;ux/=L;uy/=L;function head(px,py,dx,dy){return ' M '+px+' '+py+' L '+(px-(dx*hd)-(dy*hd*0.6)).toFixed(1)+' '+(py-(dy*hd)+(dx*hd*0.6)).toFixed(1)+' M '+px+' '+py+' L '+(px-(dx*hd)+(dy*hd*0.6)).toFixed(1)+' '+(py-(dy*hd)-(dx*hd*0.6)).toFixed(1);}return 'M '+x1+' '+y1+' L '+x2+' '+y2+head(x2,y2,ux,uy)+head(x1,y1,-ux,-uy);}
function buildVectorPath(type,w,h){if(type==='cloud')return buildCloudPath(w,h);if(type==='line')return buildLinePath(w,h);if(type==='darrow')return buildDArrowPath(w,h);return buildArrowPath(w,h);}
function renderTextAnnotation(ann, layer, W, H){var d=document.createElement('div');d.className='edm-annotation text';d.dataset.annId=ann.id;d.style.left=(ann.x*W/100)+'px';d.style.top=(ann.y*H/100)+'px';d.style.color=ann.color;d.textContent=ann.content||'';if(ann.is_resolved)d.classList.add('resolved');var del=document.createElement('div');del.className='edm-ann-delete';del.textContent='\u00d7';del.addEventListener('click',function(e){e.stopPropagation();deleteAnnotation(ann.id);});d.appendChild(del);layer.appendChild(d);}
function renderStampAnnotation(ann, layer, W, H){var d=document.createElement('div');d.className='edm-annotation stamp';d.dataset.annId=ann.id;d.style.left=(ann.x*W/100)+'px';d.style.top=(ann.y*H/100)+'px';d.style.color=ann.color;d.style.borderColor=ann.color;d.textContent=ann.content||'STAMP';if(ann.is_resolved)d.classList.add('resolved');var del=document.createElement('div');del.className='edm-ann-delete';del.textContent='\u00d7';del.addEventListener('click',function(e){e.stopPropagation();deleteAnnotation(ann.id);});d.appendChild(del);layer.appendChild(d);}
function openSignaturePad(){
    var old=document.getElementById('edm-sign-modal'); if(old) old.remove();
    var m=document.createElement('div'); m.id='edm-sign-modal';
    m.innerHTML='<div class="edm-sign-box"><div class="edm-sign-head">Draw your signature</div>'
      +'<canvas id="edm-sign-canvas" width="460" height="170"></canvas>'
      +'<div class="edm-sign-actions"><button class="edm-popup-btn cancel" id="edm-sign-clear">Clear</button>'
      +'<button class="edm-popup-btn cancel" id="edm-sign-cancel">Cancel</button>'
      +'<button class="edm-popup-btn save" id="edm-sign-use">Use signature</button></div></div>';
    document.body.appendChild(m);
    var cv=document.getElementById('edm-sign-canvas'); var ctx=cv.getContext('2d');
    ctx.lineWidth=2.5; ctx.lineCap='round'; ctx.lineJoin='round'; ctx.strokeStyle=State.color||'#1f2533';
    var drawing=false,last=null,hasInk=false;
    function pos(e){var r=cv.getBoundingClientRect();var t=e.touches?e.touches[0]:e;return {x:t.clientX-r.left,y:t.clientY-r.top};}
    function down(e){drawing=true;last=pos(e);e.preventDefault();}
    function move(e){if(!drawing)return;var p=pos(e);ctx.beginPath();ctx.moveTo(last.x,last.y);ctx.lineTo(p.x,p.y);ctx.stroke();last=p;hasInk=true;e.preventDefault();}
    function up(){drawing=false;}
    cv.addEventListener('mousedown',down);cv.addEventListener('mousemove',move);window.addEventListener('mouseup',up);
    cv.addEventListener('touchstart',down);cv.addEventListener('touchmove',move);window.addEventListener('touchend',up);
    document.getElementById('edm-sign-clear').onclick=function(){ctx.clearRect(0,0,cv.width,cv.height);hasInk=false;};
    document.getElementById('edm-sign-cancel').onclick=function(){m.remove();};
    document.getElementById('edm-sign-use').onclick=function(){
        if(!hasInk){toast('Please draw a signature first',true);return;}
        State.pendingSignature=cv.toDataURL('image/png'); m.remove(); setTool('signature');
        toast('Click on the PDF to place your signature');
    };
}
function renderSignatureAnnotation(ann, layer, W, H){
    var d=document.createElement('div'); d.className='edm-annotation signature'; d.dataset.annId=ann.id;
    d.style.left=(ann.x*W/100)+'px'; d.style.top=(ann.y*H/100)+'px';
    d.style.width=(ann.width*W/100)+'px'; d.style.height=(ann.height*H/100)+'px';
    if(ann.is_resolved)d.classList.add('resolved');
    if(ann.path_data){var img=document.createElement('img');img.src=ann.path_data;img.style.width='100%';img.style.height='100%';img.style.objectFit='contain';img.draggable=false;d.appendChild(img);}
    var del=document.createElement('div');del.className='edm-ann-delete';del.textContent='\u00d7';del.addEventListener('click',function(e){e.stopPropagation();deleteAnnotation(ann.id);});d.appendChild(del);
    layer.appendChild(d);
}
function renderShapeAnnotation(ann, layer, W, H) {
    const div = document.createElement('div');
    div.className = `edm-annotation ${ann.annotation_type}`;
    div.dataset.annId = ann.id;
    div.style.left = (ann.x * W / 100) + 'px';
    div.style.top = (ann.y * H / 100) + 'px';
    div.style.width = (ann.width * W / 100) + 'px';
    div.style.height = (ann.height * H / 100) + 'px';
    div.style.backgroundColor = ann.color;
    div.style.borderColor = ann.color;
    div.style.color = ann.color;
    div.style.opacity = ann.opacity;
    if (ann.is_resolved) div.classList.add('resolved');

    if (['cloud','arrow','line','darrow'].includes(ann.annotation_type)) {
        var pxW=Math.max(ann.width*W/100,1), pxH=Math.max(ann.height*H/100,1);
        div.style.backgroundColor='transparent'; div.style.border='none';
        var NS='http://www.w3.org/2000/svg';
        var sv=document.createElementNS(NS,'svg');
        sv.setAttribute('width','100%'); sv.setAttribute('height','100%');
        sv.setAttribute('viewBox','0 0 '+pxW+' '+pxH); sv.setAttribute('preserveAspectRatio','none');
        sv.style.overflow='visible';
        var pth=document.createElementNS(NS,'path');
        pth.setAttribute('d', buildVectorPath(ann.annotation_type,pxW,pxH));
        pth.setAttribute('fill','none'); pth.setAttribute('stroke',ann.color);
        pth.setAttribute('stroke-width','2.5'); pth.setAttribute('stroke-linejoin','round'); pth.setAttribute('stroke-linecap','round');
        sv.appendChild(pth); div.appendChild(sv);
    }

    // delete button
    const del = document.createElement('div');
    del.className = 'edm-ann-delete';
    del.textContent = '×';
    del.addEventListener('click', e => { e.stopPropagation(); deleteAnnotation(ann.id); });
    div.appendChild(del);

    // click to show note
    if (ann.content) {
        div.title = ann.content;
    }

    layer.appendChild(div);
}

function renderNoteAnnotation(ann, layer, W, H) {
    const pin = document.createElement('div');
    pin.className = 'edm-annotation note-pin';
    pin.dataset.annId = ann.id;
    pin.style.left = (ann.x * W / 100) + 'px';
    pin.style.top = (ann.y * H / 100) + 'px';
    pin.style.backgroundColor = ann.color;
    pin.title = ann.content || '(no text)';
    if (ann.is_resolved) pin.classList.add('resolved');
    pin.innerHTML = `<span>📝</span>`;

    const del = document.createElement('div');
    del.className = 'edm-ann-delete';
    del.textContent = '×';
    del.addEventListener('click', e => { e.stopPropagation(); deleteAnnotation(ann.id); });
    pin.appendChild(del);

    layer.appendChild(pin);
}

function renderDrawingAnnotation(ann, svg) {
    if (!ann.path_data) return;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', ann.path_data);
    path.setAttribute('stroke', ann.color);
    path.setAttribute('stroke-width', '3');
    path.setAttribute('fill', 'none');
    path.setAttribute('opacity', ann.opacity);
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(path);
}

// ---------------------------------------------------------------
// 8.  Sidebar
// ---------------------------------------------------------------
function renderSidebar() {
    const list = document.getElementById('edm-annotation-list');
    const count = document.getElementById('edm-ann-count');
    count.textContent = State.annotations.length;

    list.innerHTML = '';
    if (State.description && State.description.trim()) {
        const dc = document.createElement('div');
        dc.className = 'edm-desc-card';
        dc.innerHTML = '<div class="edm-desc-card-label"><i class="fa fa-align-left"></i> Description</div>'
                     + '<div class="edm-desc-card-text">' + escHtml(State.description) + '</div>';
        list.appendChild(dc);
    }
    if (!State.annotations.length) {
        const empty = document.createElement('div');
        empty.style.cssText = 'color:#888;font-size:12px;text-align:center;padding:20px;';
        empty.textContent = 'No annotations yet';
        list.appendChild(empty);
        return;
    }

    State.annotations.forEach(ann => {
        const item = document.createElement('div');
        item.className = 'edm-ann-item' + (ann.is_resolved ? ' resolved-item' : '');
        item.style.borderLeftColor = ann.color;

        item.innerHTML = `
<div class="edm-ann-item-header">
    <span class="edm-ann-type-badge" style="background:${ann.color};color:#000;">${ann.annotation_type}</span>
    <span class="edm-ann-page">P.${ann.page_number}</span>
</div>
${ann.content ? `<div class="edm-ann-content">${escHtml(ann.content)}</div>` : ''}
<div style="color:#888;font-size:10px;margin-top:3px;">${ann.user_name || ''}</div>
<div class="edm-ann-actions">
    <button class="edm-ann-act-btn" data-go="${ann.id}">Go to</button>
    <button class="edm-ann-act-btn" data-resolve="${ann.id}">${ann.is_resolved ? 'Reopen' : 'Resolve'}</button>
    <button class="edm-ann-act-btn danger" data-delete="${ann.id}">Delete</button>
</div>`;

        item.querySelector('[data-go]').addEventListener('click', () => {
            if (ann.page_number !== State.currentPage) renderPage(ann.page_number);
        });
        item.querySelector('[data-resolve]').addEventListener('click', () => toggleResolve(ann.id, !ann.is_resolved));
        item.querySelector('[data-delete]').addEventListener('click', () => deleteAnnotation(ann.id));

        list.appendChild(item);
    });
}

function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---------------------------------------------------------------
// 9.  Save annotation
// ---------------------------------------------------------------
async function saveAnnotation(annData) {
    const result = await rpc('/edm/annotation/save', annData);
    if (result && result.status === 'ok') {
        // update local
        const idx = State.annotations.findIndex(a => a.id === result.id);
        if (idx === -1) {
            annData.id = result.id;
            State.annotations.push(annData);
        } else {
            State.annotations[idx] = { ...State.annotations[idx], ...annData };
        }
        renderAnnotations();
        renderSidebar();
        toast('Annotation saved');
    }
}

async function deleteAnnotation(id) {
    const result = await rpc('/edm/annotation/delete', { id });
    if (result && result.status === 'ok') {
        State.annotations = State.annotations.filter(a => a.id !== id);
        renderAnnotations();
        renderSidebar();
        toast('Annotation deleted');
    }
}

async function undoAnnotation() {
    if (!State.annotations.length) { toast('Nothing to undo', true); return; }
    var ann = State.annotations[State.annotations.length - 1];
    if (!State.redoStack) State.redoStack = [];
    State.redoStack.push(Object.assign({}, ann));
    await deleteAnnotation(ann.id);
}

async function redoAnnotation() {
    if (!State.redoStack || !State.redoStack.length) { toast('Nothing to redo', true); return; }
    var data = State.redoStack.pop();
    delete data.id;
    await saveAnnotation(data);
}

async function toggleResolve(id, resolved) {
    const result = await rpc('/edm/annotation/resolve', { id, resolved });
    if (result && result.status === 'ok') {
        const ann = State.annotations.find(a => a.id === id);
        if (ann) ann.is_resolved = resolved;
        renderAnnotations();
        renderSidebar();
        toast(resolved ? 'Marked resolved' : 'Reopened');
    }
}

// ---------------------------------------------------------------
// 10.  Mouse interaction
// ---------------------------------------------------------------
let dragStart = null;

function setupMouseEvents() {
    const layer = document.getElementById('edm-annotation-layer');

    layer.addEventListener('mousedown', onMouseDown);
    layer.addEventListener('mousemove', onMouseMove);
    layer.addEventListener('mouseup', onMouseUp);
}

function getRelPos(e) {
    const rect = document.getElementById('edm-pdf-canvas').getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width * 100;
    const y = (e.clientY - rect.top) / rect.height * 100;
    return { x, y };
}

function onMouseDown(e) {
    if (State.currentTool === 'select') return;
    e.preventDefault();

    const pos = getRelPos(e);

    if (State.currentTool === 'text') {
        var txt = window.prompt('Enter text:');
        if (txt) { saveAnnotation({document_id:State.documentId, annotation_type:'text', page_number:State.currentPage, x:pos.x, y:pos.y, width:0, height:0, color:State.color, opacity:1, content:txt, path_data:''}); }
        return;
    }
    if (State.currentTool === 'stamp') {
        var ssel = document.getElementById('edm-stamp-select');
        saveAnnotation({document_id:State.documentId, annotation_type:'stamp', page_number:State.currentPage, x:pos.x, y:pos.y, width:0, height:0, color:State.color, opacity:1, content:(ssel?ssel.value:'APPROVED'), path_data:''});
        return;
    }
    if (State.currentTool === 'signature') {
        if (State.pendingSignature) {
            saveAnnotation({document_id:State.documentId, annotation_type:'signature', page_number:State.currentPage, x:pos.x, y:pos.y, width:22, height:9, color:State.color, opacity:1, content:'', path_data:State.pendingSignature});
        } else { toast('Open the Signature tool first', true); }
        return;
    }
    if (State.currentTool === 'note') {
        State.noteTarget = { x: pos.x, y: pos.y, page: State.currentPage };
        openNotePopup(e.clientX, e.clientY, null, null);
        return;
    }

    if (State.currentTool === 'drawing') {
        State.isDrawing = true;
        State.drawPath = [pos];
        return;
    }

    // rect / highlight / underline / strikethrough
    dragStart = pos;
    State.pendingAnnotation = null;
}

function onMouseMove(e) {
    if (State.currentTool === 'drawing' && State.isDrawing) {
        const pos = getRelPos(e);
        State.drawPath.push(pos);
        drawLivePreview();
        return;
    }

    if (!dragStart) return;
    const pos = getRelPos(e);
    State.pendingAnnotation = makePending(dragStart, pos);
    renderAnnotations();
    drawPendingRect(State.pendingAnnotation);
}

function onMouseUp(e) {
    if (State.currentTool === 'drawing' && State.isDrawing) {
        State.isDrawing = false;
        if (State.drawPath.length > 2) {
            const pathData = buildSvgPath(State.drawPath);
            const ann = {
                document_id: State.documentId,
                annotation_type: 'drawing',
                page_number: State.currentPage,
                x: 0, y: 0, width: 0, height: 0,
                color: State.color,
                opacity: State.opacity,
                content: '',
                path_data: pathData,
            };
            saveAnnotation(ann);
        }
        State.drawPath = [];
        clearLivePreview();
        return;
    }

    if (!dragStart) return;
    const pos = getRelPos(e);
    const pending = makePending(dragStart, pos);

    if (Math.abs(pending.width) > 1 && Math.abs(pending.height) > 1) {
        const ann = {
            document_id: State.documentId,
            annotation_type: State.currentTool,
            page_number: State.currentPage,
            x: pending.x,
            y: pending.y,
            width: Math.abs(pending.width),
            height: Math.abs(pending.height),
            color: State.color,
            opacity: State.opacity,
            content: '',
            path_data: '',
        };
        saveAnnotation(ann);
    }

    dragStart = null;
    State.pendingAnnotation = null;
    renderAnnotations();
}

function makePending(start, end) {
    return {
        x: Math.min(start.x, end.x),
        y: Math.min(start.y, end.y),
        width: Math.abs(end.x - start.x),
        height: Math.abs(end.y - start.y),
    };
}

// Live drag preview
let previewEl = null;
function drawPendingRect(p) {
    if (!previewEl) {
        previewEl = document.createElement('div');
        previewEl.style.cssText = 'position:absolute;pointer-events:none;z-index:10;';
        document.getElementById('edm-annotation-layer').appendChild(previewEl);
    }
    const canvas = document.getElementById('edm-pdf-canvas');
    const W = canvas.width, H = canvas.height;
    previewEl.style.left = (p.x * W / 100) + 'px';
    previewEl.style.top = (p.y * H / 100) + 'px';
    previewEl.style.width = (p.width * W / 100) + 'px';
    previewEl.style.height = (p.height * H / 100) + 'px';

    const t = State.currentTool;
    if (['rectangle','square','ellipse','cloud','arrow'].includes(t)) {
        previewEl.style.border = `2px dashed ${State.color}`;
        previewEl.style.background = 'transparent';
        previewEl.style.opacity = '1';
        previewEl.style.borderRadius = (t==='ellipse')?'50%':'0';
    } else {
        previewEl.style.background = State.color;
        previewEl.style.opacity = State.opacity * 0.7;
        previewEl.style.border = 'none';
    }
}

// Live drawing preview
let livePath = null;
function drawLivePreview() {
    const svg = document.getElementById('edm-drawing-svg');
    if (livePath) svg.removeChild(livePath);
    if (State.drawPath.length < 2) return;
    livePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    livePath.setAttribute('d', buildSvgPath(State.drawPath));
    livePath.setAttribute('stroke', State.color);
    livePath.setAttribute('stroke-width', '3');
    livePath.setAttribute('fill', 'none');
    livePath.setAttribute('opacity', State.opacity);
    livePath.setAttribute('stroke-linecap', 'round');
    livePath.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(livePath);
}

function clearLivePreview() {
    const svg = document.getElementById('edm-drawing-svg');
    if (livePath) { svg.removeChild(livePath); livePath = null; }
}

function buildSvgPath(pts) {
    const canvas = document.getElementById('edm-pdf-canvas');
    const W = canvas.width, H = canvas.height;
    const abs = pts.map(p => ({ x: p.x * W / 100, y: p.y * H / 100 }));
    let d = `M ${abs[0].x} ${abs[0].y}`;
    for (let i = 1; i < abs.length; i++) d += ` L ${abs[i].x} ${abs[i].y}`;
    return d;
}

// ---------------------------------------------------------------
// 11.  Note popup
// ---------------------------------------------------------------
let _noteEditId = null;
function openNotePopup(clientX, clientY, editId, existingText) {
    _noteEditId = editId;
    const popup = document.getElementById('edm-note-popup');
    const ta = document.getElementById('edm-note-text');
    ta.value = existingText || '';
    popup.style.left = Math.min(clientX, window.innerWidth - 280) + 'px';
    popup.style.top = Math.min(clientY, window.innerHeight - 160) + 'px';
    popup.classList.add('visible');
    ta.focus();
}

function closeNotePopup() {
    document.getElementById('edm-note-popup').classList.remove('visible');
    State.noteTarget = null;
    _noteEditId = null;
}

// ---------------------------------------------------------------
// 12.  Export notes as text
// ---------------------------------------------------------------
function _loadLib(src, check, cb){
    if (check()) { cb(); return; }
    var sc=document.createElement('script'); sc.src=src; sc.onload=cb; sc.onerror=function(){ toast('Could not load export library', true); }; document.head.appendChild(sc);
}
async function downloadAnnotatedPdf(){
    toast('Preparing annotated PDF...');
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', function(){return window.jspdf && window.jspdf.jsPDF;}, res); });
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', function(){return window.html2canvas;}, res); });
    if(!window.jspdf || !window.html2canvas){ toast('Export library failed to load', true); return; }
    var JsPDF = window.jspdf.jsPDF;
    var pdf=null; var keep=State.currentPage;
    for (var p=1; p<=State.totalPages; p++){
        await renderPage(p);
        await new Promise(function(r){ setTimeout(r, 280); });
        var wrap=document.getElementById('edm-pdf-page-wrapper');
        var shot=await window.html2canvas(wrap, {backgroundColor:'#ffffff', scale:1.5, useCORS:true, logging:false});
        var img=shot.toDataURL('image/png'); var w=shot.width, h=shot.height;
        var orient = w>=h ? 'l' : 'p';
        if(!pdf){ pdf=new JsPDF({orientation:orient, unit:'pt', format:[w,h]}); }
        else { pdf.addPage([w,h], orient); }
        pdf.addImage(img, 'PNG', 0, 0, w, h);
    }
    var t=(document.getElementById('edm-file-title')||{}).textContent||'document';
    t=t.replace(/\.pdf$/i,'');
    pdf.save(t+'_annotated.pdf');
    await renderPage(keep);
    toast('Annotated PDF downloaded');
}
async function saveAnnotatedVersion(){
    toast('Building version...');
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', function(){return window.jspdf && window.jspdf.jsPDF;}, res); });
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', function(){return window.html2canvas;}, res); });
    if(!window.jspdf || !window.html2canvas){ toast('Export library failed to load', true); return; }
    var JsPDF = window.jspdf.jsPDF; var pdf=null; var keep=State.currentPage;
    for (var p=1; p<=State.totalPages; p++){
        await renderPage(p); await new Promise(function(r){ setTimeout(r, 280); });
        var wrap=document.getElementById('edm-pdf-page-wrapper');
        var shot=await window.html2canvas(wrap, {backgroundColor:'#ffffff', scale:1.5, useCORS:true, logging:false});
        var img=shot.toDataURL('image/png'); var w=shot.width, h=shot.height; var o=w>=h?'l':'p';
        if(!pdf){ pdf=new JsPDF({orientation:o, unit:'pt', format:[w,h]}); } else { pdf.addPage([w,h], o); }
        pdf.addImage(img, 'PNG', 0, 0, w, h);
    }
    await renderPage(keep);
    var uri=pdf.output('datauristring');
    var t=(document.getElementById('edm-file-title')||{}).textContent||'document'; t=t.replace(/\.pdf$/i,'');
    var fd=new FormData(); fd.append('document_id', State.documentId); fd.append('pdf_data', uri); fd.append('file_name', t+'_annotated.pdf');
    try{ var resp=await fetch('/edm/annotation/save_version',{method:'POST',body:fd}); var d=await resp.json();
        if(d && d.status==='ok'){ toast('Saved as version v'+d.version_no); } else { toast((d&&d.message)||'Could not save version', true); }
    }catch(e){ toast('Could not save version', true); }
}
async function shareAnnotatedPdf(){
    toast('Preparing share link...');
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js', function(){return window.jspdf && window.jspdf.jsPDF;}, res); });
    await new Promise(function(res){ _loadLib('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', function(){return window.html2canvas;}, res); });
    if(!window.jspdf || !window.html2canvas){ toast('Export library failed to load', true); return; }
    var JsPDF=window.jspdf.jsPDF; var pdf=null; var keep=State.currentPage;
    for (var p=1; p<=State.totalPages; p++){
        await renderPage(p); await new Promise(function(r){ setTimeout(r, 280); });
        var wrap=document.getElementById('edm-pdf-page-wrapper');
        var shot=await window.html2canvas(wrap, {backgroundColor:'#ffffff', scale:1.5, useCORS:true, logging:false});
        var img=shot.toDataURL('image/png'); var w=shot.width, h=shot.height; var o=w>=h?'l':'p';
        if(!pdf){ pdf=new JsPDF({orientation:o, unit:'pt', format:[w,h]}); } else { pdf.addPage([w,h], o); }
        pdf.addImage(img,'PNG',0,0,w,h);
    }
    await renderPage(keep);
    var uri=pdf.output('datauristring');
    var fd=new FormData(); fd.append('document_id', State.documentId); fd.append('pdf_data', uri);
    try{ var resp=await fetch('/edm/annotation/share',{method:'POST',body:fd}); var d=await resp.json();
        if(d && d.status==='ok'){ showShareLink(d.url); } else { toast((d&&d.message)||'Could not create share link', true); }
    }catch(e){ toast('Could not create share link', true); }
}
function showShareLink(url){
    var old=document.getElementById('edm-share-modal'); if(old) old.remove();
    var m=document.createElement('div'); m.id='edm-share-modal';
    m.innerHTML='<div class="edm-share-box"><div class="edm-sign-head">Share annotated PDF</div>'
      +'<div style="font-size:12px;color:#6b7280;margin-bottom:10px">Anyone with this link can view and download the annotated PDF.</div>'
      +'<input id="edm-share-url" readonly value="'+url+'" style="width:100%;padding:9px;border:1px solid #dfe2e9;border-radius:9px;font-size:12.5px"/>'
      +'<div class="edm-sign-actions"><button class="edm-popup-btn cancel" id="edm-share-close">Close</button>'
      +'<button class="edm-popup-btn save" id="edm-share-copy">Copy link</button></div></div>';
    document.body.appendChild(m);
    document.getElementById('edm-share-close').onclick=function(){m.remove();};
    document.getElementById('edm-share-copy').onclick=function(){
        var inp=document.getElementById('edm-share-url'); inp.select();
        try{ navigator.clipboard.writeText(inp.value); }catch(e){ try{document.execCommand('copy');}catch(e2){} }
        toast('Link copied');
    };
}
function exportNotes() {
    if (!State.annotations.length) { toast('No annotations to export', true); return; }
    let txt = `Annotations for Document ID: ${State.documentId}\n`;
    txt += '='.repeat(50) + '\n\n';
    State.annotations.forEach((a, i) => {
        txt += `[${i + 1}] Type: ${a.annotation_type}  |  Page: ${a.page_number}  |  Author: ${a.user_name}\n`;
        if (a.content) txt += `    Note: ${a.content}\n`;
        if (a.is_resolved) txt += `    ✓ Resolved\n`;
        txt += '\n';
    });
    const blob = new Blob([txt], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `annotations_doc_${State.documentId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------
// 13.  Tool selection helper
// ---------------------------------------------------------------
function updateStatusBar(){
    var p=document.getElementById('edm-sb-page'); if(p) p.textContent='Page '+State.currentPage+' / '+State.totalPages;
    var z=document.getElementById('edm-sb-zoom'); if(z) z.textContent=Math.round((State.scale||1)*100)+'%';
    var labels={select:'Select',highlight:'Highlight',underline:'Underline',strikethrough:'Strikethrough',rectangle:'Rectangle',square:'Square',ellipse:'Circle',cloud:'Cloud',arrow:'Arrow',line:'Line',darrow:'Double arrow',note:'Note',text:'Text',stamp:'Stamp',signature:'Signature',drawing:'Draw'};
    var t=document.getElementById('edm-sb-tool'); if(t) t.textContent=labels[State.currentTool]||State.currentTool||'Select';
}
function ensureNavbar(){
    if(document.getElementById('edm-annotator-navbar')) return;
    var ov=document.getElementById('edm-pdf-annotator-overlay'); if(!ov) return;
    var nav=document.createElement('div'); nav.id='edm-annotator-navbar';
    nav.innerHTML='<div class="edm-nav-left"><span class="edm-nav-apps"><i class="fa fa-file-text-o"></i></span><span class="edm-nav-title">Document Annotator</span></div>'
        +'<div class="edm-nav-right"><button class="edm-nav-close" title="Close"><i class="fa fa-times"></i></button></div>';
    ov.insertBefore(nav, ov.firstChild);
    var cb=nav.querySelector('.edm-nav-close');
    if(cb) cb.addEventListener('click', function(){ var x=document.getElementById('edm-close-annotator'); if(x){ x.click(); } else { ov.classList.remove('active'); } });
}
function buildOdooMenus(){
    var ov=document.getElementById('edm-pdf-annotator-overlay'); if(!ov) return;
    var nav=document.getElementById('edm-annotator-navbar'); if(!nav) return;
    if(document.getElementById('edm-menubar')) return;
    var groups={
        'Markup':['edm-tool-highlight','edm-tool-underline','edm-tool-strikethrough'],
        'Shapes':['edm-tool-rectangle','edm-tool-square','edm-tool-ellipse','edm-tool-cloud','edm-tool-line','edm-tool-arrow','edm-tool-darrow'],
        'Insert':['edm-tool-text','edm-tool-note','edm-tool-stamp','edm-tool-signature']
    };
    var menubar=document.createElement('div'); menubar.id='edm-menubar'; menubar.className='edm-menubar';
    var subrow=document.createElement('div'); subrow.id='edm-submenu-row'; subrow.className='edm-submenu-row';
    function closeAll(){
        menubar.querySelectorAll('.edm-menu-item').forEach(function(x){x.classList.remove('active');});
        subrow.querySelectorAll('.edm-submenu').forEach(function(x){x.classList.remove('active');});
        subrow.classList.remove('open');
    }
    Object.keys(groups).forEach(function(label){
        var m=document.createElement('button'); m.type='button'; m.className='edm-menu-item'; m.innerHTML='<span>'+label+'</span><i class="fa fa-angle-down edm-menu-caret"></i>';
        var sub=document.createElement('div'); sub.className='edm-submenu';
        groups[label].forEach(function(id){ var b=document.getElementById(id); if(b) sub.appendChild(b); });
        if(label==='Insert'){
            var sel=document.getElementById('edm-stamp-select');
            if(sel){ var w=document.createElement('span'); w.className='edm-submenu-extra'; w.appendChild(document.createTextNode('Stamp Type ')); w.appendChild(sel); sub.appendChild(w); }
        }
        subrow.appendChild(sub);
        m.addEventListener('click', function(e){
            e.stopPropagation();
            var wasOpen=m.classList.contains('active');
            closeAll();
            if(!wasOpen){ m.classList.add('active'); sub.classList.add('active'); subrow.classList.add('open'); }
        });
        menubar.appendChild(m);
    });
    var draw=document.createElement('button'); draw.type='button'; draw.className='edm-menu-item'; draw.textContent='Draw';
    draw.addEventListener('click', function(e){ e.stopPropagation(); closeAll(); setTool('drawing'); });
    menubar.appendChild(draw);
    var left=nav.querySelector('.edm-nav-left'); if(left){ left.appendChild(menubar); } else { nav.appendChild(menubar); }
    nav.parentNode.insertBefore(subrow, nav.nextSibling);
    var center=document.querySelector('#edm-annotator-toolbar .edm-tb-center'); if(center) center.style.display='none';
    var selBtn=document.getElementById('edm-tool-select'); if(selBtn) selBtn.style.display='none';
    var color=document.querySelector('#edm-annotator-toolbar .edm-tb-color');
    var rightSec=document.getElementById('edm-undo') ? document.getElementById('edm-undo').parentNode : null;
    if(color && rightSec){ color.style.display='flex'; rightSec.insertBefore(color, rightSec.firstChild); }
    document.addEventListener('click', function(e){ if(!subrow.contains(e.target) && !menubar.contains(e.target)) closeAll(); });
}
function enhanceOdooBar(){
    var nav=document.getElementById('edm-annotator-navbar'); if(!nav) return;
    var menubar=document.getElementById('edm-menubar');
    var subrow=document.getElementById('edm-submenu-row');
    if(!menubar||!subrow) return;
    if(document.getElementById('edm-menu-file')) return;
    function addMenu(id,label,ids){
        var m=document.createElement('button'); m.type='button'; m.id=id; m.className='edm-menu-item'; m.innerHTML='<span>'+label+'</span><i class="fa fa-angle-down edm-menu-caret"></i>';
        var sub=document.createElement('div'); sub.className='edm-submenu';
        ids.forEach(function(x){ var b=document.getElementById(x); if(b) sub.appendChild(b); });
        subrow.appendChild(sub);
        m.addEventListener('click', function(e){
            e.stopPropagation();
            var was=m.classList.contains('active');
            menubar.querySelectorAll('.edm-menu-item').forEach(function(z){z.classList.remove('active');});
            subrow.querySelectorAll('.edm-submenu').forEach(function(z){z.classList.remove('active');});
            subrow.classList.remove('open');
            if(!was){ m.classList.add('active'); sub.classList.add('active'); subrow.classList.add('open'); }
        });
        menubar.appendChild(m);
    }
    addMenu('edm-menu-view','View',['edm-zoom-out','edm-zoom-in']);
    addMenu('edm-menu-file','File',['edm-export-btn','edm-download-pdf','edm-save-version','edm-share-pdf']);
    var right=nav.querySelector('.edm-nav-right');
    var close=right ? right.querySelector('.edm-nav-close') : null;
    function ins(el,cls){ if(el && right){ if(cls) el.classList.add(cls); if(close) right.insertBefore(el,close); else right.appendChild(el); } }
    var color=document.querySelector('.edm-tb-color'); if(color){ color.style.display='flex'; ins(color,'edm-systray-color'); }
    ins(document.getElementById('edm-undo'),'edm-systray-btn');
    ins(document.getElementById('edm-redo'),'edm-systray-btn');
    ins(document.getElementById('edm-save-all'),'edm-systray-save');
    var sb=document.getElementById('edm-annotator-statusbar');
    var pagenav=document.querySelector('#edm-annotator-toolbar .edm-tb-pagenav') || document.querySelector('.edm-tb-pagenav');
    if(sb && pagenav){
        sb.insertBefore(pagenav, sb.firstChild);
        var sbpage=document.getElementById('edm-sb-page'); if(sbpage && sbpage.closest('.edm-sb-item')) sbpage.closest('.edm-sb-item').style.display='none';
    }
    var tb=document.getElementById('edm-annotator-toolbar'); if(tb) tb.style.display='none';
}
function ensureStatusBar(){
    if(document.getElementById('edm-annotator-statusbar')) return;
    var ov=document.getElementById('edm-pdf-annotator-overlay'); if(!ov) return;
    var sb=document.createElement('div'); sb.id='edm-annotator-statusbar';
    sb.innerHTML='<span class="edm-sb-item"><i class="fa fa-file-text-o"></i> <span id="edm-sb-page">Page 1 / 1</span></span>'
        +'<span class="edm-sb-item"><i class="fa fa-search-plus"></i> <span id="edm-sb-zoom">150%</span></span>'
        +'<span class="edm-sb-item"><i class="fa fa-mouse-pointer"></i> <span id="edm-sb-tool">Select</span></span>'
        +'<span class="edm-sb-spacer"></span>'
        +'<span class="edm-sb-brand">InomERP \u00b7 Document Annotator</span>';
    ov.appendChild(sb);
}
function setTool(tool) {
    State.currentTool = tool;
    document.querySelectorAll('.edm-tool-btn').forEach(b => b.classList.remove('active'));

    const map = {
        select: 'edm-tool-select',
        highlight: 'edm-tool-highlight',
        underline: 'edm-tool-underline',
        strikethrough: 'edm-tool-strikethrough',
        rectangle: 'edm-tool-rectangle',
        square: 'edm-tool-square',
        ellipse: 'edm-tool-ellipse',
        cloud: 'edm-tool-cloud',
        arrow: 'edm-tool-arrow',
        line: 'edm-tool-line',
        darrow: 'edm-tool-darrow',
        text: 'edm-tool-text',
        stamp: 'edm-tool-stamp',
        signature: 'edm-tool-signature',
        note: 'edm-tool-note',
        drawing: 'edm-tool-drawing',
    };
    const el = document.getElementById(map[tool]);
    if (el) el.classList.add('active');

    const layer = document.getElementById('edm-annotation-layer');
    layer.className = 'drawing-mode'; // pointer-events on
    if (tool === 'select') layer.className = ''; // disable drawing events
    if (tool === 'note') layer.className = 'note-mode';
    if (typeof updateStatusBar === 'function') updateStatusBar();
}

// ---------------------------------------------------------------
// 14.  Wire up toolbar events (called once per open)
// ---------------------------------------------------------------
let eventsWired = false;
function wireToolbarEvents() {
    if (eventsWired) return;
    eventsWired = true;

    document.getElementById('edm-tool-select').addEventListener('click', () => setTool('select'));
    var _tb = document.getElementById('edm-annotator-toolbar'); var _ddwired=1;
    if (_tb) {
        _tb.addEventListener('click', function(ev){
            var trg = ev.target.closest('.edm-dd-trigger');
            if (trg) { var dd=trg.parentElement; var was=dd.classList.contains('open');
                _tb.querySelectorAll('.edm-dd.open').forEach(function(o){o.classList.remove('open');});
                if(!was) dd.classList.add('open'); ev.stopPropagation(); return; }
            if (ev.target.closest('.edm-dd-item')) { _tb.querySelectorAll('.edm-dd.open').forEach(function(o){o.classList.remove('open');}); }
        });
        document.addEventListener('click', function(){ _tb.querySelectorAll('.edm-dd.open').forEach(function(o){o.classList.remove('open');}); });
    }
    document.getElementById('edm-tool-highlight').addEventListener('click', () => setTool('highlight'));
    document.getElementById('edm-tool-underline').addEventListener('click', () => setTool('underline'));
    document.getElementById('edm-tool-strikethrough').addEventListener('click', () => setTool('strikethrough'));
    document.getElementById('edm-tool-rectangle').addEventListener('click', () => setTool('rectangle'));
    document.getElementById('edm-tool-square').addEventListener('click', () => setTool('square'));
    document.getElementById('edm-tool-ellipse').addEventListener('click', () => setTool('ellipse'));
    document.getElementById('edm-tool-cloud').addEventListener('click', () => setTool('cloud'));
    document.getElementById('edm-tool-arrow').addEventListener('click', () => setTool('arrow'));
    document.getElementById('edm-tool-line').addEventListener('click', () => setTool('line'));
    document.getElementById('edm-tool-darrow').addEventListener('click', () => setTool('darrow'));
    document.getElementById('edm-tool-text').addEventListener('click', () => setTool('text'));
    document.getElementById('edm-tool-stamp').addEventListener('click', () => setTool('stamp'));
    document.getElementById('edm-tool-signature').addEventListener('click', () => openSignaturePad());
    document.getElementById('edm-tool-note').addEventListener('click', () => setTool('note'));
    document.getElementById('edm-tool-drawing').addEventListener('click', () => setTool('drawing'));

    document.getElementById('edm-color-picker').addEventListener('input', e => { State.color = e.target.value; });
    document.getElementById('edm-opacity-slider').addEventListener('input', e => { State.opacity = e.target.value / 100; });

    document.getElementById('edm-prev-page').addEventListener('click', () => {
        if (State.currentPage > 1) renderPage(State.currentPage - 1);
    });
    document.getElementById('edm-next-page').addEventListener('click', () => {
        if (State.currentPage < State.totalPages) renderPage(State.currentPage + 1);
    });
    document.getElementById('edm-zoom-out').addEventListener('click', () => { State.scale = Math.max(0.5, State.scale - 0.25); renderPage(State.currentPage); });
    document.getElementById('edm-zoom-in').addEventListener('click', () => { State.scale = Math.min(4, State.scale + 0.25); renderPage(State.currentPage); });
    document.getElementById('edm-undo').addEventListener('click', () => { undoAnnotation(); });
    document.getElementById('edm-redo').addEventListener('click', () => { redoAnnotation(); });

    document.getElementById('edm-save-all').addEventListener('click', () => {
        toast('All annotations are auto-saved ✓');
    });

    document.getElementById('edm-export-btn').addEventListener('click', exportNotes);
    document.getElementById('edm-download-pdf').addEventListener('click', downloadAnnotatedPdf);
    document.getElementById('edm-save-version').addEventListener('click', saveAnnotatedVersion);
    var descSaveBtn = document.getElementById('edm-desc-save');
    if (descSaveBtn) {
        descSaveBtn.addEventListener('click', async function () {
            var el = document.getElementById('edm-desc-text');
            var text = el ? el.value : '';
            var res = await rpc('/edm/annotation/description', { document_id: State.documentId, description: text });
            if (res && res.status === 'ok') { State.description = text; renderSidebar(); if (el) { el.value = ''; } toast('Description saved'); }
            else { toast('Could not save description'); }
        });
        var descLiveEl = document.getElementById('edm-desc-text');
        if (descLiveEl) {
            descLiveEl.addEventListener('input', function () {
                State.description = descLiveEl.value;
                renderSidebar();
            });
        }
    }
    document.getElementById('edm-share-pdf').addEventListener('click', shareAnnotatedPdf);

    document.getElementById('edm-close-annotator').addEventListener('click', closeAnnotator);

    document.getElementById('edm-note-save').addEventListener('click', () => {
        const text = document.getElementById('edm-note-text').value.trim();
        if (_noteEditId) {
            // editing existing
            rpc('/edm/annotation/save', { id: _noteEditId, content: text }).then(() => {
                const a = State.annotations.find(x => x.id === _noteEditId);
                if (a) a.content = text;
                renderAnnotations(); renderSidebar();
                toast('Note updated');
            });
        } else if (State.noteTarget) {
            const ann = {
                document_id: State.documentId,
                annotation_type: 'note',
                page_number: State.noteTarget.page,
                x: State.noteTarget.x, y: State.noteTarget.y,
                width: 0, height: 0,
                color: State.color,
                opacity: 1,
                content: text,
                path_data: '',
            };
            saveAnnotation(ann);
        }
        closeNotePopup();
    });

    document.getElementById('edm-note-cancel').addEventListener('click', closeNotePopup);

    // keyboard shortcuts
    document.addEventListener('keydown', e => {
        const overlay = document.getElementById('edm-pdf-annotator-overlay');
        if (!overlay.classList.contains('active')) return;
        if (e.key === 'Escape') closeAnnotator();
        if (e.key === 'ArrowLeft') { if (State.currentPage > 1) renderPage(State.currentPage - 1); }
        if (e.key === 'ArrowRight') { if (State.currentPage < State.totalPages) renderPage(State.currentPage + 1); }
    });

    setupMouseEvents();
}

// ---------------------------------------------------------------
// 15.  Open / Close
// ---------------------------------------------------------------
function closeAnnotator() {
    const overlay = document.getElementById('edm-pdf-annotator-overlay');
    overlay.classList.remove('active');
    State.pdfDoc = null;
}

export async function openAnnotator(documentId, fileBase64, fileName) {
    buildOverlay();
    wireToolbarEvents();

    State.documentId = documentId;
    State.currentPage = 1;
    State.annotations = [];
    State.currentTool = 'select';

    const overlay = document.getElementById('edm-pdf-annotator-overlay');
    overlay.classList.add('active');

    setTool('select');
    ensureNavbar();
    buildOdooMenus();
    enhanceOdooBar();
    ensureStatusBar();
    updateStatusBar();

    // Reset color/opacity UI
    document.getElementById('edm-color-picker').value = '#FFFF00';
    document.getElementById('edm-opacity-slider').value = 50;
    State.color = '#FFFF00';
    State.opacity = 0.5;

    // Check it is PDF
    if (!fileName || !fileName.toLowerCase().endsWith('.pdf')) {
        toast('PDF annotation is only available for PDF files', true);
        overlay.classList.remove('active');
        return;
    }

    ensurePdfJs(async () => {
        try {
            const pdfData = atob(fileBase64);
            const uint8 = new Uint8Array(pdfData.length);
            for (let i = 0; i < pdfData.length; i++) uint8[i] = pdfData.charCodeAt(i);

            State.pdfDoc = await window.pdfjsLib.getDocument({ data: uint8 }).promise;
            State.totalPages = State.pdfDoc.numPages;

            await fitToWidth();
            await renderPage(1);
            await loadAnnotations();
        } catch (err) {
            console.error('PDF.js error:', err);
            toast('Could not load PDF: ' + err.message, true);
        }
    });
}
