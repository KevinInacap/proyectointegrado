const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
module.exports = function () {
    const template = fs.readFileSync(path.join(root, 'templates/activities/dashboard_admin.html'), 'utf8');
    return [...template.matchAll(/static 'js\/admin\/([^']+)'/g)]
        .map(match => fs.readFileSync(path.join(root, 'static/js/admin', match[1]), 'utf8')).join('\n');
};
