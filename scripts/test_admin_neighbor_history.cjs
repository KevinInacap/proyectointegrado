const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const s = require('./admin_test_source.cjs')();
function section(a,b) {const i=s.indexOf(a), j=s.indexOf(b,i); assert.ok(i>=0&&j>i); return s.slice(i,j);}
const nodes = Object.fromEntries(['fichaNombre','fichaRut','fichaDireccion','fichaTelefono','fichaTerritorio','fichaEstado','fichaHistorialTickets'].map(id => [id,{textContent:'',innerHTML:''}]));
const attack='<img src=x onerror=alert(1)>';
let shown=0, status=true;
const ctx=vm.createContext({
    document:{getElementById:id=>nodes[id]}, datasetVecinos:[{id:1,nombre:'Ana',rut:'1',direccion:'Calle',telefono:'123',territorio:'Centro',estado:'Activo'}],
    bsModalFicha:{show(){shown++;}},
    fetch:async()=>({ok:status,json:async()=>status ? {success:true,recent_attentions:[{code:attack,subject:attack,status:'Pendiente',date:'2026-01-01'}]} : {success:false}})
});
vm.runInContext(section('        function escapeHtml(', '        let calFechaActual'),ctx);
vm.runInContext(section('        let fichaVecinoRequestId', '        function exportarFichaIndividualPDF'),ctx);
(async()=>{
 await ctx.abrirFichaVecino(1);
 assert.equal(shown,1);
 assert.equal(nodes.fichaHistorialTickets.innerHTML.includes(attack),false);
 assert.ok(nodes.fichaHistorialTickets.innerHTML.includes('&lt;img src=x onerror=alert(1)&gt;'));
 status=false; await ctx.abrirFichaVecino(1);
 assert.match(nodes.fichaHistorialTickets.textContent,/No se pudo cargar/);
 console.log('OK: ficha de vecino consulta historial real y protege el contenido.');
})().catch(e=>{console.error(e);process.exitCode=1;});
