/**
 * F5 BIG-IP ASM Challenge Solver
 * Evaluates the client proof-of-work challenge script returned by CGV Vietnam
 */
const vm = require('vm');
const fs = require('fs');

function solveChallenge(html) {
    const scriptMatch = html.match(/<script type="text\/javascript">([\s\S]*?)<\/script>/);
    if (!scriptMatch) return null;

    let submittedForm = null;
    let setCookies = [];

    // Extract input fields from form
    const inputMatches = [...html.matchAll(/<input type="hidden" name="([^"]+)" value="([^"]*)"/g)];
    const elements = inputMatches.map(m => ({ name: m[1], value: m[2] }));

    const actionMatch = html.match(/action="([^"]+)"/);
    const formAction = actionMatch ? actionMatch[1] : "%2fdefault%2fmovies%2fnow-showing.html";

    const mockDocument = {
        forms: [
            {
                action: formAction,
                attributes: {
                    action: { value: formAction }
                },
                elements: elements,
                submit: function() {
                    submittedForm = {
                        action: this.action,
                        elements: this.elements.map(e => ({ name: e.name, value: e.value }))
                    };
                }
            }
        ],
        get cookie() { return ""; },
        set cookie(val) { setCookies.push(val); }
    };

    const mockWindow = {
        location: {
            replace: function(url) {
                // Not standard for F5 POST, but mock it
            }
        }
    };

    const sandbox = {
        document: mockDocument,
        window: mockWindow,
        decodeURIComponent: decodeURIComponent,
        parseInt: parseInt,
        Math: Math,
        Array: Array,
        String: String,
        Date: Date,
        console: console
    };

    try {
        vm.createContext(sandbox);
        vm.runInContext(scriptMatch[1], sandbox);
        if (typeof sandbox.challenge === 'function') {
            sandbox.challenge();
        }
        return {
            success: true,
            action: submittedForm ? submittedForm.action : formAction,
            elements: submittedForm ? submittedForm.elements : []
        };
    } catch (e) {
        return {
            success: false,
            error: e.message
        };
    }
}

// Read HTML from stdin or argument file
if (require.main === module) {
    const filePath = process.argv[2];
    if (filePath && fs.existsSync(filePath)) {
        const html = fs.readFileSync(filePath, 'utf8');
        const res = solveChallenge(html);
        console.log(JSON.stringify(res));
    } else {
        let inputData = '';
        process.stdin.setEncoding('utf8');
        process.stdin.on('data', chunk => { inputData += chunk; });
        process.stdin.on('end', () => {
            const res = solveChallenge(inputData);
            console.log(JSON.stringify(res));
        });
    }
}

module.exports = { solveChallenge };
