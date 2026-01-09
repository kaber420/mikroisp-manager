# app/services/base_service.py
"""
BaseCRUDService: Generic service class for standard CRUD operations.
Reduces code duplication across domain-specific services.
"""
from typing import TypeVar, Generic, Type, List, Dict, Any, Optional
from sqlmodel import Session, select
from fastapi import HTTPException

# Generic type for SQLModel models
ModelType = TypeVar("ModelType")


class BaseCRUDService(Generic[ModelType]):
    """
    Base class providing generic CRUD (Create, Read, Update, Delete) operations.
    
    Usage:
        class MyService(BaseCRUDService[MyModel]):
            def __init__(self, session: Session):
                super().__init__(session, MyModel)
    """
    
    def __init__(self, session: Session, model: Type[ModelType]):
        """
        Initialize the service with a database session and model class.
        
        Args:
            session: SQLModel database session.
            model: The SQLModel class this service manages.
        """
        self.session = session
        self.model = model

    def get_all(self) -> List[ModelType]:
        """Retrieve all records of the model."""
        statement = select(self.model)
        return self.session.exec(statement).all()

    def get_by_id(self, id: int) -> ModelType:
        """
        Retrieve a single record by its primary key.
        
        Args:
            id: The primary key of the record.
            
        Returns:
            The model instance.
            
        Raises:
            HTTPException: 404 if not found.
        """
        record = self.session.get(self.model, id)
        if not record:
            raise HTTPException(status_code=404, detail=f"{self.model.__name__} no encontrado")
        return record

    def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values.
            
        Returns:
            The created model instance.
        """
        try:
            new_record = self.model(**data)
            self.session.add(new_record)
            self.session.commit()
            self.session.refresh(new_record)
            return new_record
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error creando {self.model.__name__}: {str(e)}")

    def update(self, id: int, data: Dict[str, Any]) -> ModelType:
        """
        Update an existing record.
        
        Args:
            id: The primary key of the record to update.
            data: Dictionary of field values to update.
            
        Returns:
            The updated model instance.
            
        Raises:
            HTTPException: 404 if not found.
        """
        record = self.get_by_id(id)  # Raises HTTPException if not found
        
        for key, value in data.items():
            setattr(record, key, value)
        
        try:
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Error actualizando {self.model.__name__}: {str(e)}")

    def delete(self, id: int) -> None:
        """
        Delete a record by its primary key.
        
        Args:
            id: The primary key of the record to delete.
            
        Raises:
            HTTPException: 404 if not found.
        """
        record = self.get_by_id(id)  # Raises HTTPException if not found
        self.session.delete(record)
        self.session.commit()
