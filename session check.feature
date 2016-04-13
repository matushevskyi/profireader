# Created by grekas at 26.02.16
Feature: Session Scenario
  Checking all possibilities

  Scenario: №1 Без підтвердження пошти
    # Enter steps here
  1 Чистка кешу
  2 Реєстрація на профірідері без підтвердження пошти
  3 Захід на родинні фірми
  4 на родинних фірмах і матеріалах родинних фірм сесія не підміняється

    Scenario: №2 без будь якої логінації на профірідері
    # Enter steps here
  1 Чистка кешу
  2 вхід на http://rodynni.firmy/ без реєстрації/логінації профірідері
  3 вибрання будь яких статей(details + id) і перехід на них, авто-рефреш сторінки статті яку ми вибрали(details)
  4 в кукісах присвоюється сесія з профірідера, і разом присвоюється локальна сесія родинних фірм(інша): "Cookie:beaker.session.id=424275d0c4774dc69407fc4ec50eb438; beaker.session.id=d5d08d99a0b548629a08408fc721f8d1"

    Scenario: №3 з підтвердженням пошти
    # Enter steps here
  1 Чистка кешу
  2 Реєстрація на профірідері з підтвердженням пошти
  3 Захід на родинні фірми, авто-рефреш сторінки, сесія підміняється на прорідерську
  4 при переході на будь яку статтю (details + id), сесія далі профірідерська без змін
  5 при повернені на http://rodynni.firmy/  через активну кнопку "Родинні фірми" біля статті  виникає помилка "sqlalchemy.orm.exc.NoResultFound
    sqlalchemy.orm.exc.NoResultFound: No row was found for one()" за URL https://profireader.com/company/profile/560b9f54-1727-4001-bda8-784be5762873/

      Scenario: №4 Без логінації на профірідері з двома вкладками родинних фірм
    # Enter steps here
  1 Чистка кешу
  2 захід на  http://rodynni.firmy/ , потім в іншій вкладці на http://rodynni.firmy/,
  3 стається авторефреш зразу на 2 вкладці після загрузки, і на ній же присвоюється сесія з профірідера
  4 Захід на 1 вкладці на статтю, сесія також змінюється на профірідерську

      Scenario: №5 Логінація з двох акаунтів одночасно на різних вкладках
    # Enter steps here
  1 Чистка кешу
  2 захід на  https://profireader.com/auth/login_signup/?login_signup=login , потім в іншій вкладці на https://profireader.com/auth/login_signup/?login_signup=login/,
  3 логінація на одній greckasus@ на іншій alex_alex_123@
  4 beaker.session.id= на вкладках різний поки не клікнути на 2 вкладці кудись, далі присвоюється beaker.session.id= з першої вкладки і залогований відповідно тільки перший юзер.

      Scenario: №6 робота з фірмами після перезагрузки ПК, зі збереженим юзером на профірідері(chrome)
    # Enter steps here
  1 загрузка браузера
  2 захід на  https://profireader.com/#_=_ (провірка чи юзер залогований), потім в двох інших вкладках на http://rodynni.firmy/details/56ce8d24-141c-4001-bdf4-bc84be65d851; і http://rodynni.firmy/details/56c58481-1d17-4001-923b-858f481b21a1,
  3 на http://rodynni.firmy/details/56ce8d24-141c-4001-bdf4-bc84be65d851 пише що я не залогований: "This article can read only by users which are logged in.
    Click here to log in"
  4 в кукісах знову дві різних сесії beaker.session.id=611a995fb342482bb9624bdd71bae485; beaker.session.id=a63a615b94de4041943496a887a3934c
  5 якщо повернутись назад на http://rodynni.firmy/ і звідти знову зайти на http://rodynni.firmy/details/56ce8d24-141c-4001-bdf4-bc84be65d851
    тоді все починає працювати корректно, в кукісах дублюється але однакова: Cookie:beaker.session.id=611a995fb342482bb9624bdd71bae485; beaker.session.id=611a995fb342482bb9624bdd71bae485

      Scenario: №7 Без підтвердження пошти, логінація на профірідері + 2 вкладки rodynni.firmy
    # Enter steps here
  1 Чистка кешу
  2 захід на  http://rodynni.firmy/details/56c58481-1d17-4001-923b-858f481b21a1 , потім в іншій вкладці на http://rodynni.firmy/details/56ce8d24-141c-4001-bdf4-bc84be65d851,
  3 на перші родинні фірми зайшло без застереження про необхідність логінації, на другі написало "This article can read only by users which are logged in.
     Click here to log in"
  4 сесії в кукісах на профірідері відрізняються від вкладок на родинних фірмах, сесії на родинних фірмах НЕ дублюються.
  5 при заході на новини http://rodynni.firmy/%D0%9D%D0%BE%D0%B2%D0%B8%D0%BD%D0%B8/1/?search_text=, або інший основний розділ(Новини Статті Події Співпраця Компанії Купуймо разом Про нас), періодично в кукісах змінюється beaker.session.id на новий