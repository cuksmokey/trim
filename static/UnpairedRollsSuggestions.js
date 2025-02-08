// UnpairedRollsSuggestions.js
const UnpairedRollsSuggestions = function(props) {
    const remainingRolls = props.remainingRolls || [];
    const maxWidth = props.maxWidth || 312;

    if (!remainingRolls || !Array.isArray(remainingRolls) || remainingRolls.length === 0) {
        return null;
    }

    const suggestions = remainingRolls
        .filter(function(roll) { 
            return Array.isArray(roll) && roll.length >= 3 && roll[2] > 0;
        })
        .map(function(roll) {
            const width = roll[0];
            const quantity = roll[2];
            const suggestedWidth = maxWidth - width;
            
            if (!width || !quantity || suggestedWidth <= 0) return null;
            
            return {
                originalWidth: width,
                suggestedWidth: suggestedWidth,
                quantity: quantity
            };
        })
        .filter(function(suggestion) { return suggestion !== null; });

    if (suggestions.length === 0) {
        return null;
    }

    return React.createElement('div', { style: { marginTop: '1rem' } },
        React.createElement('h5', { style: { marginBottom: '0.5rem', fontWeight: 500 } }, 
            'Suggested Pairs for Remaining Rolls'
        ),
        React.createElement('table', { style: { width: '100%', borderCollapse: 'collapse' } },
            React.createElement('thead', null,
                React.createElement('tr', null,
                    React.createElement('th', { style: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' } }, 
                        'Current Width'
                    ),
                    React.createElement('th', { style: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' } }, 
                        'Suggested Pair Width'
                    ),
                    React.createElement('th', { style: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' } }, 
                        'Quantity Needed'
                    ),
                    React.createElement('th', { style: { border: '1px solid #ddd', padding: '8px', textAlign: 'left' } }, 
                        'Total Width'
                    )
                )
            ),
            React.createElement('tbody', null,
                suggestions.map(function(suggestion, index) {
                    return React.createElement('tr', { key: index },
                        React.createElement('td', { style: { border: '1px solid #ddd', padding: '8px' } }, 
                            suggestion.originalWidth + 'mm'
                        ),
                        React.createElement('td', { style: { border: '1px solid #ddd', padding: '8px', color: '#2563eb', fontWeight: 500 } }, 
                            suggestion.suggestedWidth + 'mm'
                        ),
                        React.createElement('td', { style: { border: '1px solid #ddd', padding: '8px' } }, 
                            suggestion.quantity
                        ),
                        React.createElement('td', { style: { border: '1px solid #ddd', padding: '8px' } }, 
                            maxWidth + 'mm'
                        )
                    );
                })
            )
        )
    );
};

// Make it available globally
window.UnpairedRollsSuggestions = UnpairedRollsSuggestions;