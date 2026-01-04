import React, { useState, useEffect, useRef } from 'react';
import './SearchableSelect.css';

function SearchableSelect({ 
  options, 
  value, 
  onChange, 
  placeholder,
  searchFields = ['print_name_part1', 'base_model_name', 'developer_id'],
  displayField = 'print_name_part1',
  valueField = 'base_model_id',
  className = '',
  disabled = false
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredOptions, setFilteredOptions] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [inputValue, setInputValue] = useState('');
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  // Find the selected option
  useEffect(() => {
    if (value && options.length > 0) {
      const found = options.find(option => 
        option[valueField] === value || option[displayField] === value
      );
      setSelectedOption(found || null);
      if (found) {
        setInputValue(found[displayField]);
      } else {
        setInputValue('');
      }
    } else {
      setSelectedOption(null);
      setInputValue('');
    }
  }, [value, options, valueField, displayField]);

  // Filter options based on search query
  useEffect(() => {
    let query = searchQuery.trim().toLowerCase();
    
    // If input is empty, show all (first 1000)
    if (!query) {
      setFilteredOptions(options.slice(0, 1000));
    } else {
      const filtered = options.filter(option => {
        return searchFields.some(field => {
          const fieldValue = option[field];
          if (typeof fieldValue === 'string') {
            return fieldValue.toLowerCase().includes(query);
          }
          return false;
        });
      }).slice(0, 1000); // Limit results
      
      setFilteredOptions(filtered);
    }
  }, [searchQuery, options, searchFields]);

  // Handle clicks outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        // Reset input to selected option display value
        if (selectedOption) {
            setInputValue(selectedOption[displayField]);
        } else {
            setInputValue('');
        }
        setSearchQuery('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [selectedOption, displayField]);

  const handleToggle = (e) => {
    if (disabled) return;
    // Don't toggle if clicking the input itself, let focus handle it
    if (e.target === inputRef.current) return;

    setIsOpen(!isOpen);
    if (!isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
      setSearchQuery(inputValue); // Filter by current input when opening
    }
  };

  const handleSelect = (option) => {
    setSelectedOption(option);
    setInputValue(option[displayField]);
    onChange(option[valueField]);
    setIsOpen(false);
    setSearchQuery('');
  };

  const handleInputChange = (e) => {
    const val = e.target.value;
    setInputValue(val);
    setSearchQuery(val);
    if (!isOpen) setIsOpen(true);
    
    // Optional: Clear selection if input doesn't match?
    // For now, we keep selectedOption until a new one is picked, 
    // or we could set it to null if we want to force re-selection.
    // Setting to null is safer if the user is typing something new.
    if (val === '') {
        setSelectedOption(null);
        onChange(null);
    }
  };

  const handleInputFocus = () => {
      if (!disabled) {
          setIsOpen(true);
          setSearchQuery(inputValue);
      }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      if (selectedOption) {
          setInputValue(selectedOption[displayField]);
      } else {
          setInputValue('');
      }
      inputRef.current?.blur();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (isOpen && filteredOptions.length > 0) {
        handleSelect(filteredOptions[0]);
      }
    }
  };

  const highlightMatch = (text, query) => {
    if (!query.trim()) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <span key={index} className="highlight">{part}</span>
      ) : part
    );
  };

  return (
    <div className={`searchable-select ${className}`} ref={dropdownRef}>
      <div 
        className={`select-trigger ${isOpen ? 'open' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={handleToggle}
      >
        <div className="selected-value">
            <input
                ref={inputRef}
                type="text"
                className="trigger-input"
                placeholder={placeholder}
                value={inputValue}
                onChange={handleInputChange}
                onFocus={handleInputFocus}
                onKeyDown={handleKeyDown}
                disabled={disabled}
            />
        </div>
        <div className="select-arrow">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 8L3 5h6l-3 3z" fill="currentColor"/>
          </svg>
        </div>
      </div>

      {isOpen && (
        <div className="select-dropdown">
          {/* Search input container removed */}
          
          <div className="options-container">
            {filteredOptions.length === 0 ? (
              <div className="no-results">
                {searchQuery ? 'No models found' : 'No options available'}
              </div>
            ) : (
              filteredOptions.map((option, index) => (
                <div
                  key={option[valueField] || index}
                  className={`option ${selectedOption?.[valueField] === option[valueField] ? 'selected' : ''}`}
                  onClick={() => handleSelect(option)}
                >
                  <div className="option-main">
                    <span className="option-text">
                      {highlightMatch(option[displayField], searchQuery)}
                    </span>
                  </div>
                  
                  {/* Additional info like cost, capabilities */}
                  {option.cost && (
                    <div className="option-info">
                      {option.cost.is_free ? (
                        <span className="cost-badge free">FREE</span>
                      ) : (
                        <span className="cost-badge">${option.cost.cost_1mT_input_USD?.toFixed(2)}/mT</span>
                      )}
                    </div>
                  )}
                  
                  {option.capabilities && (
                    <div className="capabilities">
                      {option.capabilities.toolUse && <span className="cap-badge">T</span>}
                      {option.capabilities.reasoning && <span className="cap-badge">R</span>}
                      {option.capabilities.vision && <span className="cap-badge">V</span>}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchableSelect;
