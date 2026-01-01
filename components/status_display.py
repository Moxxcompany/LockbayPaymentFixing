"""
Status Display Component

Handles transaction status updates with real-time progress tracking, error handling, and completion flows.
Supports various transaction types and provides appropriate user actions for each status.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from services.scene_engine import SceneState, ComponentConfig

logger = logging.getLogger(__name__)

class StatusDisplayComponent:
    """Component for displaying transaction status and progress"""
    
    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        scene_state: SceneState,
        component_config: ComponentConfig
    ) -> Optional[Dict[str, Any]]:
        """Process status display interaction"""
        config = component_config.config
        
        # Handle callback queries (status actions)
        if update.callback_query:
            return await self._process_callback(update, scene_state, config)
        
        # Status display is typically read-only, but can handle refresh requests
        if update.message and update.message.text:
            return await self._process_text(update, scene_state, config)
        
        return None
    
    async def _process_callback(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process callback query for status actions"""
        query = update.callback_query
        if not query or not query.data:
            return None
        
        action = query.data
        
        if action == 'refresh_status':
            # Refresh transaction status
            return await self._refresh_status(scene_state, config)
        
        elif action == 'new_transaction':
            # Start a new transaction
            return {
                'success': True,
                'data': {'action': 'new_transaction'},
                'message': "Starting new transaction...",
                'next_step': config.get('new_transaction_step', 'menu')
            }
        
        elif action == 'retry_transaction':
            # Retry failed transaction
            return await self._retry_transaction(scene_state, config)
        
        elif action == 'cancel_transaction':
            # Cancel pending transaction
            return await self._cancel_transaction(scene_state, config)
        
        elif action == 'main_menu':
            # Return to main menu
            return {
                'success': True,
                'data': {'action': 'main_menu'},
                'message': "Returning to main menu...",
                'next_step': 'menu'
            }
        
        elif action == 'transaction_details':
            # Show detailed transaction information
            return await self._show_transaction_details(scene_state, config)
        
        elif action == 'contact_support':
            # Contact support about transaction
            return {
                'success': True,
                'data': {'action': 'contact_support'},
                'message': "Connecting you with support...",
                'next_step': 'support'
            }
        
        return None
    
    async def _process_text(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process text message for status commands"""
        text = update.message.text.strip().lower()
        
        if text in ['refresh', 'status', 'update']:
            return await self._refresh_status(scene_state, config)
        
        elif text in ['details', 'info', 'information']:
            return await self._show_transaction_details(scene_state, config)
        
        return None
    
    async def _refresh_status(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh transaction status from external systems"""
        try:
            transaction_id = scene_state.data.get('transaction_id')
            if not transaction_id:
                return {
                    'success': False,
                    'error': "No transaction ID found"
                }
            
            # Query UTE for latest status
            from services.unified_transaction_engine import UnifiedTransactionEngine
            ute = UnifiedTransactionEngine()
            
            status_result = await ute.get_transaction_status(transaction_id)
            if status_result['success']:
                updated_status = status_result['data']
                
                return {
                    'success': True,
                    'data': {
                        'status_updated': True,
                        'old_status': scene_state.data.get('status'),
                        'new_status': updated_status['status'],
                        'transaction_data': updated_status
                    },
                    'message': self._format_status_update(updated_status)
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to refresh status: {status_result.get('error', 'Unknown error')}"
                }
        
        except Exception as e:
            logger.error(f"Status refresh error: {e}")
            return {
                'success': False,
                'error': "Failed to refresh status. Please try again."
            }
    
    async def _retry_transaction(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Retry a failed transaction"""
        try:
            transaction_id = scene_state.data.get('transaction_id')
            if not transaction_id:
                return {
                    'success': False,
                    'error': "No transaction to retry"
                }
            
            # Check if retry is allowed
            status = scene_state.data.get('status', '')
            if status not in ['failed', 'error', 'cancelled']:
                return {
                    'success': False,
                    'error': f"Cannot retry transaction with status: {status}"
                }
            
            # Initiate retry through UTE
            from services.unified_transaction_engine import UnifiedTransactionEngine
            ute = UnifiedTransactionEngine()
            
            retry_result = await ute.retry_transaction(transaction_id)
            if retry_result['success']:
                return {
                    'success': True,
                    'data': {
                        'retried': True,
                        'new_transaction_id': retry_result['data'].get('transaction_id'),
                        'status': 'retrying'
                    },
                    'message': "Transaction retry initiated. Processing...",
                    'next_step': 'processing'
                }
            else:
                return {
                    'success': False,
                    'error': f"Retry failed: {retry_result.get('error', 'Unknown error')}"
                }
        
        except Exception as e:
            logger.error(f"Transaction retry error: {e}")
            return {
                'success': False,
                'error': "Failed to retry transaction. Please try again."
            }
    
    async def _cancel_transaction(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a pending transaction"""
        try:
            transaction_id = scene_state.data.get('transaction_id')
            if not transaction_id:
                return {
                    'success': False,
                    'error': "No transaction to cancel"
                }
            
            # Check if cancellation is allowed
            status = scene_state.data.get('status', '')
            if status in ['completed', 'failed', 'cancelled']:
                return {
                    'success': False,
                    'error': f"Cannot cancel transaction with status: {status}"
                }
            
            # Cancel through UTE
            from services.unified_transaction_engine import UnifiedTransactionEngine
            ute = UnifiedTransactionEngine()
            
            cancel_result = await ute.cancel_transaction(transaction_id)
            if cancel_result['success']:
                return {
                    'success': True,
                    'data': {
                        'cancelled': True,
                        'status': 'cancelled'
                    },
                    'message': "Transaction cancelled successfully.",
                    'next_step': 'cancelled'
                }
            else:
                return {
                    'success': False,
                    'error': f"Cancellation failed: {cancel_result.get('error', 'Unknown error')}"
                }
        
        except Exception as e:
            logger.error(f"Transaction cancellation error: {e}")
            return {
                'success': False,
                'error': "Failed to cancel transaction. Please try again."
            }
    
    async def _show_transaction_details(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Show detailed transaction information"""
        data = scene_state.data
        details = self._format_transaction_details(data)
        
        return {
            'success': True,
            'data': {
                'details_shown': True
            },
            'message': details
        }
    
    def _format_status_update(self, transaction_data: Dict[str, Any]) -> str:
        """Format status update message"""
        status = transaction_data.get('status', 'unknown')
        
        status_messages = {
            'pending': '🔄 Transaction is pending...',
            'processing': '⏳ Transaction is being processed...',
            'completed': '✅ Transaction completed successfully!',
            'failed': '❌ Transaction failed.',
            'cancelled': '🚫 Transaction was cancelled.',
            'requires_action': '⚠️ Transaction requires your attention.'
        }
        
        message = status_messages.get(status, f"📊 Transaction status: {status}")
        
        # Add additional info based on status
        if status == 'completed':
            if 'completion_time' in transaction_data:
                message += f"\n⏰ Completed at: {transaction_data['completion_time']}"
        
        elif status == 'failed':
            if 'error_message' in transaction_data:
                message += f"\n❗ Error: {transaction_data['error_message']}"
        
        elif status == 'processing':
            if 'estimated_completion' in transaction_data:
                message += f"\n⏰ Estimated completion: {transaction_data['estimated_completion']}"
        
        return message
    
    def _format_transaction_details(self, data: Dict[str, Any]) -> str:
        """Format detailed transaction information"""
        details = ["📋 Transaction Details\n"]
        
        # Basic info
        if 'transaction_id' in data:
            details.append(f"🆔 ID: {data['transaction_id']}")
        
        if 'transaction_type' in data:
            details.append(f"🔄 Type: {data['transaction_type'].title()}")
        
        if 'status' in data:
            details.append(f"📊 Status: {data['status'].title()}")
        
        # Amount info
        if 'amount' in data:
            currency = data.get('currency', 'USD')
            details.append(f"💰 Amount: {data['amount']} {currency}")
        
        if 'fee' in data:
            details.append(f"💸 Fee: {data['fee']}")
        
        if 'total' in data:
            details.append(f"💵 Total: {data['total']}")
        
        # Destination info
        destination = data.get('destination', {})
        if isinstance(destination, dict):
            if 'bank_name' in destination:
                details.append(f"🏦 Bank: {destination['bank_name']}")
                details.append(f"👤 Account: {destination['account_name']}")
            elif 'address' in destination:
                addr = destination['address']
                details.append(f"🔗 Address: {addr}")
        
        # Timestamps
        if 'created_at' in data:
            details.append(f"📅 Created: {data['created_at']}")
        
        if 'confirmed_at' in data:
            details.append(f"✅ Confirmed: {data['confirmed_at']}")
        
        if 'completed_at' in data:
            details.append(f"🎯 Completed: {data['completed_at']}")
        
        # Provider info
        if 'provider' in data:
            details.append(f"🏗️ Provider: {data['provider']}")
        
        if 'provider_reference' in data:
            details.append(f"📝 Reference: {data['provider_reference']}")
        
        return '\n'.join(details)
    
    def _get_status_icon(self, status: str) -> str:
        """Get appropriate icon for transaction status"""
        icons = {
            'pending': '🔄',
            'processing': '⏳',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫',
            'requires_action': '⚠️',
            'retrying': '🔄'
        }
        return icons.get(status, '📊')
    
    def _estimate_completion_time(self, transaction_data: Dict[str, Any]) -> Optional[str]:
        """Estimate completion time based on transaction type and provider"""
        transaction_type = transaction_data.get('transaction_type', '')
        provider = transaction_data.get('provider', '')
        
        # Typical completion times
        if 'ngn' in transaction_type.lower() and 'fincra' in provider.lower():
            return "5-15 minutes"
        elif 'crypto' in transaction_type.lower():
            return "30-60 minutes"
        elif 'escrow' in transaction_type.lower():
            return "Immediate"
        else:
            return "Processing..."