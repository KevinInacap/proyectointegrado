const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/js/admin/neighbors.js'), 'utf8');
const start = source.indexOf('        async function guardarVecino(e)');
const end = source.indexOf('        function eliminarVecino', start);
assert.ok(start >= 0 && end > start);
const nodes = Object.fromEntries(Object.entries({vecinoId:'', vecinoNombre:'María Pérez', vecinoRut:'12345678-5',
    vecinoDireccion:'Calle 1', vecinoEmail:'maria@example.com', vecinoTelefono:'+56 9 1234 5678',
    vecinoTerritorio:'Centro', vecinoEstado:'Activo'}).map(([id, value]) => [id, {value}]));
const alerts = [];
const requests = [];
const ctx = vm.createContext({document:{getElementById:id=>nodes[id]}, datasetVecinos:[],
    Swal:{fire:o=>alerts.push(o)}, getCookie:()=>'', bsModalVecino:{hide(){}}, mostrarToast(){},
    cargarVecinosDesdeDB:async()=>{}, validarRutChileno:()=>true,
    fetch:async(url, options)=>{ requests.push(JSON.parse(options.body)); return {ok:true, json:async()=>({success:true,message:'Guardado'})}; }});
vm.runInContext(source.slice(start,end),ctx);
const event = {preventDefault(){}, currentTarget:{querySelector(){return null;}}};
(async()=>{
    await ctx.guardarVecino(event);
    assert.equal(requests.length,1, 'un correo válido debe permitir guardar');
    assert.equal(requests[0].email,'maria@example.com');
    for (const [id, bad] of [['vecinoEmail','mal@'], ['vecinoTelefono','123'], ['vecinoNombre','<script>'], ['vecinoDireccion','<img>'], ['vecinoRut','12345678-5ABC'], ['vecinoNombre','']]) {
        const previous = nodes[id].value;
        nodes[id].value = bad;
        await ctx.guardarVecino(event);
        assert.equal(requests.length,1, `${id} inválido no debe enviarse`);
        assert.ok(alerts.at(-1).icon === 'warning' || alerts.at(-1).icon === 'error');
        nodes[id].value = previous;
    }
    ctx.datasetVecinos.push({id: 7, nombre:'María Pérez', rut:'12345678-5', direccion:'Calle 1', telefono:'123456', email:'maria@example.com'});
    nodes.vecinoId.value = '7';
    nodes.vecinoTelefono.value = '123456';
    nodes.vecinoDireccion.value = 'Calle 2';
    await ctx.guardarVecino(event);
    assert.equal(requests.length,2,'un teléfono antiguo sin cambios no debe impedir corregir la dirección');
    nodes.vecinoTelefono.value = '12345';
    await ctx.guardarVecino(event);
    assert.equal(requests.length,2,'un teléfono nuevo inválido debe rechazarse');
    nodes.vecinoTelefono.value = '123456';
    ctx.cargarVecinosDesdeDB = async () => false;
    await ctx.guardarVecino(event);
    assert.equal(requests.length, 3);
    assert.equal(alerts.at(-1).icon, 'warning');
    assert.match(alerts.at(-1).text, /se guardaron.*no se pudo actualizar/i);
    let exported;
    const sheet = {'!ref':'A1:A1', A1:{t:'s', v:'=HYPERLINK("https://example.test")', f:'HYPERLINK("https://example.test")'}};
    ctx.window = {XLSX: {}};
    ctx.XLSX = {utils:{json_to_sheet:()=>sheet, book_new:()=>({}), book_append_sheet(){}}, writeFile:()=>{exported=sheet;}};
    const exportStart = source.indexOf('        function generarExcelDesdeArray');
    const exportEnd = source.indexOf('        function descargarPlantillaExcelVecinos', exportStart);
    vm.runInContext(source.slice(exportStart,exportEnd),ctx);
    ctx.generarExcelDesdeArray([{id:1,nombre:'=HYPERLINK("https://example.test")'}], 'test');
    assert.equal(exported.A1.t,'s');
    assert.equal(exported.A1.f,undefined, 'la exportación no debe contener fórmulas');
    assert.match(exported.A1.v,/^=HYPERLINK/);
    console.log('OK: validación del formulario de vecinos y correo válido.');
})().catch(error=>{console.error(error);process.exitCode=1;});
