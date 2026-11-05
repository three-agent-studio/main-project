import { Link } from 'react-router';
import { Card } from '../../shared/ui/Card';
import { Page } from '../../shared/ui/Page';

export default function HomePage() {
  return <Page title="Ваш цифровой деканат" description="Личный кабинет для учебной жизни.">
    <Card title="Личный кабинет"><p>Войдите с выданной вам тестовой учётной записью, чтобы открыть свой профиль.</p>
      <Link to="/profile">Открыть профиль →</Link>
    </Card>
    <Card title="О проекте"><p>Расписание, успеваемость, заявки и уведомления появятся по мере разработки сервиса.</p>
      <p>Сейчас доступна базовая оболочка кабинета. Все данные прототипа должны быть вымышленными.</p>
    </Card>
  </Page>;
}
