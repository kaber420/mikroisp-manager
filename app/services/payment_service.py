# app/services/payment_service.py
"""
Payment service layer using SQLModel ORM.
Replaces raw SQL queries from app/db/payments_db.py
"""
from typing import List, Dict, Any, Optional
import uuid
from sqlmodel import Session, select
from app.models import Payment


class PaymentService:
    """
    Service layer for Payment operations using SQLModel ORM.
    """
    
    def __init__(self, session: Session):
        """
        Initialize with a SQLModel session.
        
        Args:
            session: SQLModel Session instance
        """
        self.session = session
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get a single payment by ID."""
        payment = self.session.get(Payment, payment_id)
        return payment.model_dump() if payment else None
    
    def get_payments_for_client(self, client_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all payments for a client, ordered by most recent first."""
        statement = (
            select(Payment)
            .where(Payment.client_id == client_id)
            .order_by(Payment.fecha_pago.desc())
        )
        payments = self.session.exec(statement).all()
        return [payment.model_dump() for payment in payments]
    
    def create_payment(self, client_id: uuid.UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new payment record.
        
        Args:
            client_id: ID of the client making the payment
            data: Payment data (monto, mes_correspondiente, metodo_pago, notas)
        
        Returns:
            Created payment as dict
        """
        try:
            payment_data = {
                'client_id': client_id,
                'monto': data['monto'],
                'mes_correspondiente': data['mes_correspondiente'],
                'metodo_pago': data.get('metodo_pago'),
                'notas': data.get('notas')
            }
            
            new_payment = Payment(**payment_data)
            self.session.add(new_payment)
            self.session.commit()
            self.session.refresh(new_payment)
            
            return new_payment.model_dump()
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Database error: {e}")
    
    def update_payment_notes(self, payment_id: int, notas: str) -> int:
        """
        Update the notes of an existing payment.
        
        Args:
            payment_id: ID of the payment
            notas: New notes text
        
        Returns:
            Number of rows updated (0 or 1)
        """
        try:
            payment = self.session.get(Payment, payment_id)
            if not payment:
                return 0
            
            payment.notas = notas
            self.session.add(payment)
            self.session.commit()
            return 1
        except Exception as e:
            self.session.rollback()
            print(f"Error actualizando notas de pago: {e}")
            return 0
    
    def check_payment_exists(self, client_id: uuid.UUID, billing_cycle: str) -> bool:
        """
        Check if a payment already exists for a client and billing cycle.
        
        Args:
            client_id: ID of the client
            billing_cycle: Billing cycle in format 'YYYY-MM'
        
        Returns:
            True if payment exists, False otherwise
        """
        statement = select(Payment).where(
            Payment.client_id == client_id,
            Payment.mes_correspondiente == billing_cycle
        ).limit(1)
        
        payment = self.session.exec(statement).first()
        return payment is not None
