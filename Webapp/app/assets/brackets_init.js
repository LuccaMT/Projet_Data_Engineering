// Initialize brackets viewer when data is available
window.addEventListener('DOMContentLoaded', function() {
    // Listen for bracket data injections
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1 && node.classList && node.classList.contains('brackets-viewer')) {
                    initializeBracket(node);
                }
            });
        });
    });
    
    // Observe the entire document for bracket additions
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Initialize any existing brackets
    setTimeout(function() {
        document.querySelectorAll('.brackets-viewer[data-bracket]').forEach(initializeBracket);
    }, 500);
});

function initializeBracket(container) {
    if (!container || !window.bracketsViewer) {
        console.warn('Brackets viewer library not loaded');
        return;
    }
    
    const bracketJson = container.getAttribute('data-bracket');
    if (!bracketJson) {
        console.warn('No bracket data found');
        return;
    }
    
    try {
        const data = JSON.parse(bracketJson);
        
        console.log('Bracket data:', data);
        
        // Clear any existing content
        container.innerHTML = '';
        
        // Render the bracket
        window.bracketsViewer.render({
            stages: data.stages,
            matches: data.matches,
            matchGames: [],
            participants: data.participants || []
        }, {
            selector: '#' + container.id,
            participantOriginPlacement: 'before',
            separatedChildCountLabel: true,
            showSlotsOrigin: true,
            showLowerBracketSlotsOrigin: true
        });
        
        console.log('Bracket initialized:', container.id);
    } catch(e) {
        console.error('Error initializing bracket:', e);
    }
}
