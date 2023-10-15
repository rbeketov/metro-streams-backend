CREATE TABLE users (
    user_id        serial         PRIMARY KEY,
    first_name     varchar(20)    NOT NULL,
    second_name    varchar(20)    NOT NULL,
    email          varchar(30)    NOT NULL     UNIQUE,
    login          varchar(30)    NOT NULL     UNIQUE,
    password       varchar(30)    NOT NULL     UNIQUE,
    role           char(3)        NOT NULL     CHECK (role IN ('USR', 'MOD' ,'ADM')) DEFAULT 'USR'
);

CREATE TABLE types_of_modeling (
    modeling_id            serial               PRIMARY KEY,
    modeling_name          varchar(30)          NOT NULL,
    modeling_description   varchar(1000)         NOT NULL,
    modeling_price         decimal(30, 2)       NOT NULL,
    modeling_image_url     varchar(100)          NOT NULL,
    modeling_status        char(4)              CHECK (modeling_status IN ('WORK', 'DELE')) DEFAULT 'WORK'
);

CREATE TABLE applications_for_modeling (
    application_id             serial           PRIMARY KEY,
    user_id                    int,
    moderator_id               int,
    date_application_create    date             NOT NULL DEFAULT now(),
    date_application_accept    date,
    date_application_complete  date,
    metro_name                 varchar(20),
    status_application         char(4)          CHECK (status_application IN ('INTR', 'INPR', 'COMP', 'CANC', 'DELE')) DEFAULT 'INTR',

    FOREIGN KEY (user_id) REFERENCES users  (user_id),
    FOREIGN KEY (moderator_id) REFERENCES users  (user_id)
);

CREATE TABLE modeling_applications (
    modeling_id        int,
    application_id     int,
    PRIMARY KEY (modeling_id, application_id),
    FOREIGN KEY (modeling_id)        REFERENCES types_of_modeling           (modeling_id),
    FOREIGN KEY (application_id)     REFERENCES applications_for_modeling   (application_id)
);
