"""Account data access. No business logic."""

from sqlmodel import Session, select

from backend.models.account import Account


class AccountRepository:
    """Queries and transactions for connected accounts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, account_id: int) -> Account | None:
        return self._session.get(Account, account_id)

    def get_by_provider_email(self, provider: str, email: str) -> Account | None:
        statement = select(Account).where(
            Account.provider == provider, Account.email == email
        )
        return self._session.exec(statement).first()

    def list_for_user(self, user_id: int) -> list[Account]:
        statement = select(Account).where(Account.user_id == user_id)
        return list(self._session.exec(statement).all())

    def add(self, account: Account) -> Account:
        self._session.add(account)
        self._session.commit()
        self._session.refresh(account)
        return account

    def update(self, account: Account) -> Account:
        self._session.add(account)
        self._session.commit()
        self._session.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        self._session.delete(account)
        self._session.commit()
