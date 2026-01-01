"""
Bank Selector Component

Handles NGN bank account selection with saved accounts, bank search, and account verification.
Integrates with Fincra service for bank validation and account verification.
"""

import logging
from typing import Dict, Any, Optional, List

from telegram import Update
from telegram.ext import ContextTypes

from services.scene_engine import SceneState, ComponentConfig
from database import SessionLocal
from models import SavedBankAccount
from services.fincra_service import fincra_service

logger = logging.getLogger(__name__)

class BankSelectorComponent:
    """Component for handling NGN bank account selection"""
    
    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        scene_state: SceneState,
        component_config: ComponentConfig
    ) -> Optional[Dict[str, Any]]:
        """Process bank selection message"""
        config = component_config.config
        
        # Handle callback queries (saved bank selection)
        if update.callback_query:
            return await self._process_callback(update, scene_state, config)
        
        # Handle text messages (bank search/account details)
        if update.message and update.message.text:
            return await self._process_text(update, scene_state, config)
        
        return None
    
    async def _process_callback(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process callback query for saved bank selection"""
        query = update.callback_query
        if not query or not query.data:
            return None
        
        # Handle saved bank selection
        if query.data.startswith('bank_'):
            try:
                index = int(query.data.replace('bank_', ''))
                saved_banks = scene_state.data.get('saved_banks', [])
                
                if 0 <= index < len(saved_banks):
                    selected = saved_banks[index]
                    
                    # Validate saved bank account
                    validation = await self._validate_bank_account(selected)
                    
                    if validation['valid']:
                        return {
                            'success': True,
                            'data': {
                                'bank_code': selected['bank_code'],
                                'bank_name': selected['bank_name'],
                                'account_number': selected['account_number'],
                                'account_name': selected['account_name'],
                                'source': 'saved',
                                'is_default': selected.get('is_default', False),
                                'is_verified': selected.get('is_verified', False),
                                'validation': validation
                            }
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"Saved bank account is invalid: {validation['error']}"
                        }
                
            except (ValueError, IndexError) as e:
                logger.error(f"Invalid saved bank selection: {e}")
                return {
                    'success': False,
                    'error': "Invalid bank selection"
                }
        
        # Handle new bank account input trigger
        elif query.data == 'new_bank':
            # This triggers the manual bank entry flow
            return {
                'success': False,
                'message': "Please enter your bank account number (10 digits):",
                'next_step': 'enter_account_number'
            }
        
        # Handle bank search results
        elif query.data.startswith('select_bank_'):
            try:
                bank_code = query.data.replace('select_bank_', '')
                banks = scene_state.data.get('bank_search_results', [])
                
                selected_bank = None
                for bank in banks:
                    if bank['code'] == bank_code:
                        selected_bank = bank
                        break
                
                if selected_bank:
                    # Store selected bank and ask for account number
                    return {
                        'success': True,
                        'data': {
                            'selected_bank': selected_bank,
                            'bank_code': selected_bank['code'],
                            'bank_name': selected_bank['name']
                        },
                        'message': f"Selected: {selected_bank['name']}\n\nPlease enter your account number:",
                        'next_step': 'enter_account_number'
                    }
                
            except Exception as e:
                logger.error(f"Bank selection error: {e}")
                return {
                    'success': False,
                    'error': "Invalid bank selection"
                }
        
        return None
    
    async def _process_text(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process text message for bank search or account details"""
        text = update.message.text.strip()
        current_step = scene_state.data.get('bank_step', 'search')
        
        if current_step == 'search':
            # Bank name search
            return await self._handle_bank_search(text, scene_state)
        
        elif current_step == 'enter_account_number':
            # Account number validation
            return await self._handle_account_number(text, scene_state)
        
        else:
            # Default: try to parse as account number
            if self._is_account_number(text):
                return await self._handle_account_number(text, scene_state)
            else:
                return await self._handle_bank_search(text, scene_state)
    
    async def _handle_bank_search(self, search_term: str, scene_state: SceneState) -> Dict[str, Any]:
        """Handle bank name search"""
        try:
            # Get bank list from Fincra
            bank_list = await fincra_service.get_bank_list()
            if not bank_list:
                return {
                    'success': False,
                    'error': "Unable to fetch bank list. Please try again later."
                }
            
            # Search for matching banks
            search_lower = search_term.lower()
            matches = []
            for bank in bank_list:
                if search_lower in bank['name'].lower():
                    matches.append(bank)
            
            if not matches:
                return {
                    'success': False,
                    'error': f"No banks found matching '{search_term}'. Please try a different search term."
                }
            
            if len(matches) == 1:
                # Exact match - use this bank
                selected = matches[0]
                return {
                    'success': True,
                    'data': {
                        'selected_bank': selected,
                        'bank_code': selected['code'],
                        'bank_name': selected['name'],
                        'bank_search_results': matches
                    },
                    'message': f"Selected: {selected['name']}\n\nPlease enter your account number:",
                    'next_step': 'enter_account_number'
                }
            
            else:
                # Multiple matches - show selection
                return {
                    'success': True,
                    'data': {
                        'bank_search_results': matches[:5]  # Limit to 5 results
                    },
                    'message': f"Found {len(matches)} banks matching '{search_term}'. Please select:",
                    'next_step': 'select_from_results'
                }
        
        except Exception as e:
            logger.error(f"Bank search error: {e}")
            return {
                'success': False,
                'error': "Bank search failed. Please try again."
            }
    
    async def _handle_account_number(self, account_number: str, scene_state: SceneState) -> Dict[str, Any]:
        """Handle account number entry and verification"""
        # Clean account number
        account_number = account_number.replace(' ', '').replace('-', '')
        
        # Validate format
        if not self._is_account_number(account_number):
            return {
                'success': False,
                'error': "Please enter a valid 10-digit account number"
            }
        
        # Get selected bank
        selected_bank = scene_state.data.get('selected_bank')
        if not selected_bank:
            return {
                'success': False,
                'error': "Please select a bank first"
            }
        
        try:
            # Verify account with Fincra
            verification = await fincra_service.verify_bank_account(
                account_number, selected_bank['code']
            )
            
            if verification and verification.get('status') == 'success':
                account_name = verification.get('account_name', 'Unknown')
                
                return {
                    'success': True,
                    'data': {
                        'bank_code': selected_bank['code'],
                        'bank_name': selected_bank['name'],
                        'account_number': account_number,
                        'account_name': account_name,
                        'source': 'manual',
                        'verification': verification
                    }
                }
            
            else:
                error_msg = verification.get('message', 'Account verification failed')
                return {
                    'success': False,
                    'error': f"Account verification failed: {error_msg}"
                }
        
        except Exception as e:
            logger.error(f"Account verification error: {e}")
            return {
                'success': False,
                'error': "Account verification failed. Please check your details and try again."
            }
    
    def _is_account_number(self, text: str) -> bool:
        """Check if text looks like an account number"""
        # Remove spaces and hyphens
        cleaned = text.replace(' ', '').replace('-', '')
        
        # Nigerian account numbers are typically 10 digits
        return cleaned.isdigit() and len(cleaned) == 10
    
    async def _validate_bank_account(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a bank account (saved or new)"""
        required_fields = ['bank_code', 'bank_name', 'account_number', 'account_name']
        
        # Check required fields
        for field in required_fields:
            if not bank_data.get(field):
                return {
                    'valid': False,
                    'error': f"Missing required field: {field}"
                }
        
        # Validate account number format
        account_number = bank_data['account_number']
        if not self._is_account_number(account_number):
            return {
                'valid': False,
                'error': "Invalid account number format"
            }
        
        # Optional: Re-verify with Fincra for saved accounts
        # This helps ensure saved accounts are still valid
        try:
            verification = await fincra_service.verify_bank_account(
                account_number, bank_data['bank_code']
            )
            
            if verification and verification.get('status') == 'success':
                return {
                    'valid': True,
                    'account_name': verification.get('account_name'),
                    'verification': verification
                }
            else:
                return {
                    'valid': False,
                    'error': "Account verification failed"
                }
        
        except Exception as e:
            logger.warning(f"Bank validation error (allowing): {e}")
            # Allow saved accounts even if verification fails
            return {
                'valid': True,
                'warning': "Could not verify account status"
            }
    
    async def _load_saved_banks(self, user_id: int) -> List[Dict[str, Any]]:
        """Load saved bank accounts for a user - Enhanced with default selection and active filtering"""
        try:
            session = SessionLocal()
            try:
                # Filter by active accounts, order by default first, then by most recent
                banks = (
                    session.query(SavedBankAccount)
                    .filter(
                        SavedBankAccount.user_id == user_id,
                        SavedBankAccount.is_active == True  # Only show active accounts
                    )
                    .order_by(
                        SavedBankAccount.is_default.desc(),  # Default accounts first
                        SavedBankAccount.last_used.desc().nullslast(),  # Then by usage
                        SavedBankAccount.created_at.desc()  # Then by creation time
                    )
                    .limit(5)  # Limit to 5 most relevant
                    .all()
                )
                
                return [
                    {
                        'id': bank.id,
                        'bank_code': bank.bank_code,
                        'bank_name': bank.bank_name,
                        'account_number': bank.account_number,
                        'account_name': bank.account_name,
                        'label': getattr(bank, 'label', None) or f"{bank.bank_name} Account",
                        'is_default': getattr(bank, 'is_default', False),
                        'is_verified': getattr(bank, 'is_verified', False),
                        'verification_sent': getattr(bank, 'verification_sent', False),
                        'is_active': getattr(bank, 'is_active', True)
                    }
                    for bank in banks
                ]
            
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error loading saved banks: {e}")
            return []
    
    async def get_default_bank_account(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the default bank account for a user (for auto-cashout integration)"""
        try:
            session = SessionLocal()
            try:
                # Look for default bank account first
                default_bank = (
                    session.query(SavedBankAccount)
                    .filter(
                        SavedBankAccount.user_id == user_id,
                        SavedBankAccount.is_active == True,
                        SavedBankAccount.is_default == True
                    )
                    .first()
                )
                
                if default_bank:
                    return {
                        'id': default_bank.id,
                        'bank_code': default_bank.bank_code,
                        'bank_name': default_bank.bank_name,
                        'account_number': default_bank.account_number,
                        'account_name': default_bank.account_name,
                        'label': getattr(default_bank, 'label', None) or f"{default_bank.bank_name} Account",
                        'is_default': True,
                        'is_verified': getattr(default_bank, 'is_verified', False),
                        'verification_sent': getattr(default_bank, 'verification_sent', False),
                        'is_active': True
                    }
                
                # No default set, get the most recently used active account
                recent_bank = (
                    session.query(SavedBankAccount)
                    .filter(
                        SavedBankAccount.user_id == user_id,
                        SavedBankAccount.is_active == True
                    )
                    .order_by(
                        SavedBankAccount.last_used.desc().nullslast(),
                        SavedBankAccount.created_at.desc()
                    )
                    .first()
                )
                
                if recent_bank:
                    return {
                        'id': recent_bank.id,
                        'bank_code': recent_bank.bank_code,
                        'bank_name': recent_bank.bank_name,
                        'account_number': recent_bank.account_number,
                        'account_name': recent_bank.account_name,
                        'label': getattr(recent_bank, 'label', None) or f"{recent_bank.bank_name} Account",
                        'is_default': False,
                        'is_verified': getattr(recent_bank, 'is_verified', False),
                        'verification_sent': getattr(recent_bank, 'verification_sent', False),
                        'is_active': True
                    }
                
                return None
            
            finally:
                session.close()
        
        except Exception as e:
            logger.error(f"Error getting default bank account: {e}")
            return None