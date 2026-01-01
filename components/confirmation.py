"""
Confirmation Component

Handles transaction confirmation flows with detailed summaries, risk warnings, and user consent.
Supports multiple confirmation styles (simple, detailed, OTP-protected).
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes

from services.scene_engine import SceneState, ComponentConfig
from services.conditional_otp_service import ConditionalOTPService

logger = logging.getLogger(__name__)

class ConfirmationComponent:
    """Component for handling transaction confirmations"""
    
    def __init__(self):
        self.otp_service = ConditionalOTPService()
    
    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        scene_state: SceneState,
        component_config: ComponentConfig
    ) -> Optional[Dict[str, Any]]:
        """Process confirmation message"""
        config = component_config.config
        
        # Handle callback queries (confirmation buttons)
        if update.callback_query:
            return await self._process_callback(update, scene_state, config)
        
        # Handle text messages (OTP entry)
        if update.message and update.message.text:
            return await self._process_text(update, scene_state, config)
        
        return None
    
    async def _process_callback(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process callback query for confirmation actions"""
        query = update.callback_query
        if not query or not query.data:
            return None
        
        if query.data == 'confirm_yes':
            # User confirmed - check if OTP is required
            if config.get('require_otp', False):
                return await self._initiate_otp_flow(scene_state, config)
            else:
                return await self._handle_confirmation(scene_state, config, True)
        
        elif query.data == 'confirm_no':
            # User cancelled
            return await self._handle_confirmation(scene_state, config, False)
        
        elif query.data == 'request_otp':
            # Send OTP
            return await self._send_otp(scene_state, config)
        
        elif query.data == 'modify_transaction':
            # Go back to modify details
            return {
                'success': True,
                'data': {'action': 'modify'},
                'message': "Transaction cancelled. You can modify the details.",
                'next_step': config.get('modify_step', 'amount_input')
            }
        
        return None
    
    async def _process_text(
        self, 
        update: Update, 
        scene_state: SceneState, 
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process text message for OTP entry"""
        text = update.message.text.strip()
        
        # Check if we're expecting OTP
        if scene_state.data.get('awaiting_otp'):
            return await self._verify_otp(text, scene_state, config)
        
        return None
    
    async def _initiate_otp_flow(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate OTP verification flow"""
        try:
            # Check if OTP is required based on amount and user history
            amount = Decimal(str(scene_state.data.get('amount', 0)))
            user_id = scene_state.user_id
            
            otp_required = await self.otp_service.is_otp_required(user_id, amount)
            
            if not otp_required:
                # OTP not required - proceed with confirmation
                return await self._handle_confirmation(scene_state, config, True)
            
            # OTP required - request user contact method
            return {
                'success': True,
                'data': {
                    'otp_required': True,
                    'awaiting_otp_method': True
                },
                'message': "This transaction requires OTP verification. How would you like to receive your OTP?",
                'next_step': 'otp_method_selection'
            }
        
        except Exception as e:
            logger.error(f"OTP initiation error: {e}")
            # Fallback - proceed without OTP
            return await self._handle_confirmation(scene_state, config, True)
    
    async def _send_otp(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Send OTP to user"""
        try:
            user_id = scene_state.user_id
            amount = Decimal(str(scene_state.data.get('amount', 0)))
            
            # Generate and send OTP
            otp_result = await self.otp_service.generate_and_send_otp(
                user_id, 
                amount,
                scene_state.data.get('transaction_type', 'cashout')
            )
            
            if otp_result['success']:
                return {
                    'success': True,
                    'data': {
                        'otp_sent': True,
                        'awaiting_otp': True,
                        'otp_method': otp_result.get('method', 'telegram')
                    },
                    'message': f"OTP sent via {otp_result.get('method', 'Telegram')}. Please enter the code:",
                    'next_step': 'otp_verification'
                }
            else:
                return {
                    'success': False,
                    'error': f"Failed to send OTP: {otp_result.get('error', 'Unknown error')}"
                }
        
        except Exception as e:
            logger.error(f"OTP sending error: {e}")
            return {
                'success': False,
                'error': "Failed to send OTP. Please try again."
            }
    
    async def _verify_otp(self, otp_code: str, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Verify OTP code"""
        try:
            user_id = scene_state.user_id
            
            # Verify OTP
            verification = await self.otp_service.verify_otp(user_id, otp_code)
            
            if verification['success']:
                # OTP verified - proceed with confirmation
                return await self._handle_confirmation(scene_state, config, True)
            else:
                return {
                    'success': False,
                    'error': f"OTP verification failed: {verification.get('error', 'Invalid code')}"
                }
        
        except Exception as e:
            logger.error(f"OTP verification error: {e}")
            return {
                'success': False,
                'error': "OTP verification failed. Please try again."
            }
    
    async def _handle_confirmation(
        self, 
        scene_state: SceneState, 
        config: Dict[str, Any], 
        confirmed: bool
    ) -> Dict[str, Any]:
        """Handle final confirmation result"""
        if confirmed:
            # Transaction confirmed - prepare for execution
            transaction_data = self._build_transaction_data(scene_state, config)
            
            return {
                'success': True,
                'data': {
                    'confirmed': True,
                    'transaction_data': transaction_data,
                    'ready_for_execution': True
                },
                'message': "Transaction confirmed! Processing...",
                'next_step': config.get('success_step', 'processing')
            }
        else:
            # Transaction cancelled
            return {
                'success': True,
                'data': {
                    'confirmed': False,
                    'cancelled': True
                },
                'message': "Transaction cancelled.",
                'next_step': config.get('cancel_step', 'cancelled')
            }
    
    def _build_transaction_data(self, scene_state: SceneState, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive transaction data for execution"""
        data = scene_state.data.copy()
        
        # Add confirmation metadata
        data.update({
            'confirmed_at': scene_state.updated_at.isoformat(),
            'confirmation_method': config.get('confirmation_method', 'standard'),
            'otp_verified': data.get('otp_verified', False),
            'scene_id': scene_state.scene_id,
            'user_id': scene_state.user_id
        })
        
        # Add risk assessment if configured
        if config.get('include_risk_assessment'):
            data['risk_assessment'] = self._assess_transaction_risk(data)
        
        return data
    
    def _assess_transaction_risk(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess transaction risk level"""
        risk_score = 0
        risk_factors = []
        
        # Amount-based risk
        amount = Decimal(str(transaction_data.get('amount', 0)))
        if amount > 1000:
            risk_score += 2
            risk_factors.append('High amount')
        elif amount > 500:
            risk_score += 1
            risk_factors.append('Medium amount')
        
        # Destination-based risk
        if transaction_data.get('source') == 'manual':
            risk_score += 1
            risk_factors.append('New destination')
        
        # Transaction type risk
        transaction_type = transaction_data.get('transaction_type', '')
        if 'crypto' in transaction_type.lower():
            risk_score += 1
            risk_factors.append('Cryptocurrency transaction')
        
        # Determine risk level
        if risk_score >= 4:
            risk_level = 'HIGH'
        elif risk_score >= 2:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'requires_manual_review': risk_level == 'HIGH'
        }
    
    def _format_confirmation_summary(self, scene_state: SceneState, config: Dict[str, Any]) -> str:
        """Format transaction summary for confirmation"""
        data = scene_state.data
        summary_parts = []
        
        # Transaction type
        transaction_type = data.get('transaction_type', 'Transaction')
        summary_parts.append(f"🔄 {transaction_type.title()}")
        
        # Amount
        if 'amount' in data:
            currency = data.get('currency', 'USD')
            amount = data['amount']
            summary_parts.append(f"💰 Amount: {amount} {currency}")
        
        # Destination
        destination = data.get('destination', {})
        if isinstance(destination, dict):
            if 'bank_name' in destination:
                summary_parts.append(f"🏦 Bank: {destination['bank_name']}")
                summary_parts.append(f"👤 Account: {destination['account_name']}")
            elif 'address' in destination:
                addr = destination['address']
                summary_parts.append(f"🔗 Address: {addr[:10]}...{addr[-6:]}")
        
        # Fees
        if 'fee' in data:
            summary_parts.append(f"💸 Fee: {data['fee']}")
        
        # Total
        if 'total' in data:
            summary_parts.append(f"💵 Total: {data['total']}")
        
        # Risk warning
        risk_assessment = data.get('risk_assessment', {})
        if risk_assessment.get('risk_level') in ['MEDIUM', 'HIGH']:
            summary_parts.append(f"⚠️ Risk Level: {risk_assessment['risk_level']}")
        
        return '\n'.join(summary_parts)