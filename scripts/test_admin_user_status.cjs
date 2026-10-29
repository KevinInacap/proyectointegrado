const assert=require('node:assert/strict'), fs=require('node:fs'), vm=require('node:vm');
const source=require('./admin_test_source.cjs')();
const a=source.indexOf('        const cambiosEstadoUsuariosEnCurso'), b=source.indexOf('        async function eliminarUsuario(id)',a);
assert.ok(a>=0&&b>a);
async function scenario(confirm) {
 let requests=0; const alerts=[];
 const ctx=vm.createContext({datasetUsuarios:[{id:5,status:'Activo',full_name:'Ana'}], getCookie:()=> 'token',
 Swal:{fire:async x=>{alerts.push(x);return {isConfirmed:confirm}}},
 fetch:async()=>{requests++;return {ok:true,json:async()=>({success:true,message:'Actualizado'})}}, cargarUsuariosDesdeDB:async()=>{}});
 vm.runInContext(source.slice(a,b),ctx);await ctx.toggleEstadoUsuario(5);
 assert.equal(requests,confirm?1:0);assert.equal(alerts[0].showCancelButton,true);
 if(confirm) assert.equal(alerts[1].icon,'success');
}
Promise.all([scenario(false),scenario(true)]).then(()=>console.log('OK: cambio de estado solicita confirmación.')).catch(e=>{console.error(e);process.exitCode=1;});
