"""
Test: Seller Contact Display During Escrow Creation
Ensures buyer's entered contact shows on amount input screen, not seller's profile name
"""

import pytest


class TestSellerContactDisplayEscrowCreation:
    """Validate that escrow creation flow shows buyer's entered contact"""
    
    def test_amount_input_shows_buyer_entered_contact_not_profile(self):
        """Verify amount input screen shows buyer's contact input, not seller profile name"""
        with open('handlers/escrow.py', 'r') as f:
            escrow_source = f.read()
        
        # Find the seller_display_name assignment section
        lines = escrow_source.split('\n')
        
        # Check that we set seller_display_name from clean_seller_identifier
        initial_assignment_found = False
        for i, line in enumerate(lines):
            if 'seller_display_name = format_username_html(f"@{clean_seller_identifier}"' in line:
                initial_assignment_found = True
                break
        
        assert initial_assignment_found, \
            "Must initially set seller_display_name from clean_seller_identifier (buyer's input)"
        
        # CRITICAL: Verify we DO NOT overwrite seller_display_name with seller_profile.display_name
        overwrite_found = False
        for i, line in enumerate(lines):
            if 'seller_display_name = format_username_html(f"@{seller_profile.display_name}"' in line:
                # Check if this line is commented out or in a comment block
                if not line.strip().startswith('#'):
                    overwrite_found = True
                    break
        
        assert not overwrite_found, \
            "Must NOT overwrite seller_display_name with seller_profile.display_name - keep buyer's entered contact"
        
        print("✅ PASS: Amount input shows buyer's entered contact, not seller's profile name")
    
    def test_escrow_creation_flow_preserves_buyer_input(self):
        """Verify escrow creation preserves buyer's original contact input"""
        with open('handlers/escrow.py', 'r') as f:
            escrow_source = f.read()
        
        # Verify we have the fix comment explaining the change
        assert 'DO NOT overwrite seller_display_name' in escrow_source or \
               'Keep using the buyer' in escrow_source, \
            "Must document the fix to prevent regression"
        
        # Verify Trading with: uses seller_display_name
        assert 'Trading with: {seller_display_name}' in escrow_source, \
            "Amount input must display 'Trading with: {seller_display_name}'"
        
        print("✅ PASS: Escrow creation flow preserves buyer's contact input")
    
    def test_seller_profile_display_logic_fixed(self):
        """Verify seller profile display logic no longer overwrites buyer input"""
        with open('handlers/escrow.py', 'r') as f:
            escrow_source = f.read()
        
        # Check that we removed the problematic overwrite lines
        # Lines 757-759 used to overwrite seller_display_name
        problematic_patterns = [
            'seller_display_name = format_username_html(f"@{seller_profile.display_name}"',
            'seller_display_name = html.escape(seller_profile.display_name'
        ]
        
        # Get the section after seller_profile check
        if 'if seller_profile:' in escrow_source:
            start_idx = escrow_source.find('if seller_profile:')
            # Check next 1000 chars for problematic overwrites
            section = escrow_source[start_idx:start_idx+1000]
            
            for pattern in problematic_patterns:
                # Make sure these overwrites are NOT present (or are commented out)
                if pattern in section:
                    # Check if it's in a comment
                    lines = section.split('\n')
                    for line in lines:
                        if pattern in line and not line.strip().startswith('#'):
                            raise AssertionError(
                                f"Found problematic overwrite: {pattern}. "
                                "This overwrites buyer's contact with seller's profile name!"
                            )
        
        print("✅ PASS: Seller profile logic no longer overwrites buyer's contact input")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
