const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/js/admin/form-feedback.js'), 'utf8');
const handlers = {};
const phone = {id:'vecinoTelefono', value:'123456', type:'tel', maxLength:20, required:false,
    setAttribute(){}, focus(){}, checkValidity:()=>true, labels:[{textContent:'Teléfono'}]};
const form = {querySelectorAll:()=>[phone]};
let alerts = 0;
const document = {
    addEventListener:(name, fn)=>{handlers[name]=fn;},
    querySelectorAll:()=>[], querySelector:()=>null,
    getElementById:id=>id === 'vecinoId' ? {value:'7'} : null,
};
const context = vm.createContext({document, window:{datasetVecinos:[{id:7,telefono:'123456'}]},
    Swal:{fire(){alerts++; return Promise.resolve();}}, MutationObserver:class {observe(){}},
    requestAnimationFrame(){}, queueMicrotask(){}});
vm.runInContext(source, context);
handlers.DOMContentLoaded();
let stopped = false;
const submit = () => handlers.submit({target:form, preventDefault(){stopped=true;}, stopImmediatePropagation(){}});
submit();
assert.equal(stopped,false,'el dato antiguo sin cambios no debe bloquear la edición');
phone.value = '12345';
submit();
assert.equal(stopped,true,'un teléfono inválido modificado debe bloquearse');
assert.equal(alerts,1);
console.log('OK: validación global permite datos antiguos sin cambios y rechaza datos nuevos inválidos.');
